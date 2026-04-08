"""
Gold Layer ELT Pipeline for Analytics & BI Serving.

This script represents the final stage of the data pipeline. It reads and executes 
SQL Data Definition Language (DDL) scripts to create or update Views and Materialized 
Views in the 'gold' schema. It then dynamically discovers and refreshes all 
Materialized Views to ensure downstream dashboards and BI tools have the freshest data.
It employs advanced PostgreSQL features like concurrent refreshes for zero-downtime updates.
"""

import os
import logging
from pathlib import Path
import psycopg2
# Importing specific PostgreSQL exception types to handle fallback logic gracefully during view refreshes
from psycopg2.errors import FeatureNotSupported, ObjectNotInPrerequisiteState
from dotenv import load_dotenv

# Load database credentials from a local .env file to keep secrets out of version control
load_dotenv()

# ==========================================
# CONFIGURATION & LOGGING
# ==========================================
class Config:
    """Centralized configuration for database connections and file paths."""
    # Database connection parameters with safe default fallbacks
    DB_HOST = os.getenv("DB_HOST", "localhost")
    DB_PORT = os.getenv("DB_PORT", "5432")
    DB_NAME = os.getenv("DB_NAME", "CoinFlow")
    DB_USER = os.getenv("DB_USER", "CoinFlow")
    DB_PASSWORD = os.getenv("DB_PASSWORD", "coinflow")
    
    # Path where the Gold layer SQL scripts (defining business logic and aggregates) are stored
    GOLD_SQL_DIR = Path("../sql/gold")
    LOG_DIR = Path("../logs/gold")

def setup_logging():
    """Configures centralized logging to both the console and a persistent log file."""
    # Ensure the log directory exists before attempting to write to it
    Config.LOG_DIR.mkdir(parents=True, exist_ok=True)
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(message)s",
        handlers=[
            logging.FileHandler(Config.LOG_DIR / "gold_pipeline.log"),
            logging.StreamHandler() # Also output to console for easy monitoring
        ]
    )

# ==========================================
# DATABASE OPERATIONS
# ==========================================
def execute_ddl_scripts(conn):
    """
    Reads and executes all SQL files in the gold directory.
    This creates or updates the Views and Materialized Views definitions.
    """
    logger = logging.getLogger(__name__)
    
    # Grab all .sql files and sort them alphabetically.
    # Sorting is a crucial pattern here: it enforces execution order (e.g., "01_base_view.sql", 
    # "02_aggregated_matview.sql") to respect database dependencies.
    sql_files = sorted(list(Config.GOLD_SQL_DIR.glob("*.sql")))
    
    if not sql_files:
        logger.warning(f"No SQL files found in {Config.GOLD_SQL_DIR}. Skipping DDL execution.")
        return

    with conn.cursor() as cur:
        # Ensure the target schema exists before attempting to deploy objects into it
        cur.execute("CREATE SCHEMA IF NOT EXISTS gold;")
        logger.info("Checked/Created 'gold' schema.")

        for sql_file in sql_files:
            logger.info(f"Applying schema script: {sql_file.name}...")
            
            with open(sql_file, 'r') as file:
                sql_query = file.read()
            
            try:
                # Execute the SQL script. This typically contains CREATE OR REPLACE VIEW statements.
                cur.execute(sql_query)
                logger.info(f"✅ Successfully executed {sql_file.name}")
            except Exception as file_error:
                # Hard fail: If a core view fails to build due to a syntax error or missing table, 
                # we must halt the pipeline immediately to prevent downstream data corruption.
                logger.error(f"❌ Failed to execute {sql_file.name}: {file_error}")
                raise file_error

def refresh_materialized_views(conn):
    """
    Dynamically discovers all Materialized Views in the 'gold' schema and refreshes them.
    Attempts a zero-downtime CONCURRENT refresh first, falling back to a standard refresh.
    """
    logger = logging.getLogger(__name__)
    
    with conn.cursor() as cur:
        # 1. Query PostgreSQL catalog (pg_matviews) to dynamically discover all materialized views 
        # in the gold schema. This prevents us from having to hardcode view names in Python.
        cur.execute("SELECT matviewname FROM pg_matviews WHERE schemaname = 'gold';")
        matviews = [row[0] for row in cur.fetchall()]

        if not matviews:
            logger.info("No materialized views found in the 'gold' schema to refresh.")
            return

        # 2. Iterate through discovered views and refresh their underlying data
        for mv_name in matviews:
            logger.info(f"Refreshing materialized view: gold.{mv_name}...")
            
            try:
                # Attempt concurrent refresh. This is highly preferred because it updates the data
                # without placing an exclusive lock on the view, meaning BI tools/Dashboards can 
                # still read the old data while the new data calculates in the background.
                cur.execute(f"REFRESH MATERIALIZED VIEW CONCURRENTLY gold.{mv_name};")
                logger.info(f"✅ Successfully refreshed gold.{mv_name} (CONCURRENTLY)")
                
            except FeatureNotSupported:
                # PostgreSQL requires a UNIQUE index on a materialized view to refresh it concurrently.
                # If the SQL script didn't define one, it throws this specific error. We catch it
                # and fall back to a standard, locking refresh.
                logger.warning(f"CONCURRENT refresh not supported for gold.{mv_name} (Likely missing a UNIQUE index). Falling back to standard refresh.")
                cur.execute(f"REFRESH MATERIALIZED VIEW gold.{mv_name};")
                logger.info(f"✅ Successfully refreshed gold.{mv_name} (Standard)")
                
            except ObjectNotInPrerequisiteState:
                # If a materialized view was created using the "WITH NO DATA" clause, it cannot be
                # refreshed concurrently on its very first run. It must be populated standardly first.
                logger.warning(f"Materialized view gold.{mv_name} is currently unpopulated. Falling back to standard refresh.")
                cur.execute(f"REFRESH MATERIALIZED VIEW gold.{mv_name};")
                logger.info(f"✅ Successfully populated gold.{mv_name} (Standard)")

# ==========================================
# PIPELINE ORCHESTRATION
# ==========================================
def run_pipeline():
    """Main execution orchestrator."""
    logger = logging.getLogger(__name__)
    
    # Pre-flight validation
    if not Config.DB_PASSWORD:
        logger.error("CRITICAL: DB_PASSWORD environment variable is missing.")
        return

    if not Config.GOLD_SQL_DIR.exists():
        logger.error(f"CRITICAL: Gold SQL directory not found at {Config.GOLD_SQL_DIR}")
        return

    connection_string = (
        f"host={Config.DB_HOST} port={Config.DB_PORT} dbname={Config.DB_NAME} "
        f"user={Config.DB_USER} password={Config.DB_PASSWORD}"
    )

    conn = None
    try:
        logger.info(f"Connecting to PostgreSQL database '{Config.DB_NAME}'...")
        conn = psycopg2.connect(connection_string)
        
        # CRITICAL CONFIGURATION: 
        # By default, psycopg2 wraps everything in a transaction block (BEGIN ... COMMIT).
        # However, PostgreSQL strictly forbids running REFRESH MATERIALIZED VIEW CONCURRENTLY 
        # inside a transaction block. Setting autocommit=True tells psycopg2 to execute 
        # statements immediately, bypassing the transaction wrapper.
        conn.autocommit = True 

        # Step 1: Execute scripts to create/update View and MatView definitions (Schema definition)
        execute_ddl_scripts(conn)

        # Step 2: Refresh the data within those Materialized Views (Data population)
        refresh_materialized_views(conn)

        logger.info("All Gold layer transformations applied and data refreshed successfully.")

    except psycopg2.Error as e:
        # Catch and log database-specific errors (e.g., connection drops, syntax errors)
        logger.error(f"Database error occurred: {e}")
    except Exception as e:
        # Catch-all for unexpected Python-level errors to ensure safe exit
        logger.error(f"Unexpected application error: {e}")
    finally:
        # Always clean up the database connection, regardless of success or failure
        if conn:
            conn.close()
            logger.info("Database connection closed.")

# Standard idiom to execute logic only when the script is run directly
if __name__ == "__main__":
    setup_logging()
    logging.info("--- Starting Gold ELT Pipeline ---")
    run_pipeline()
    logging.info("--- Pipeline Finished ---")