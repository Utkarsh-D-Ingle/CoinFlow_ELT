"""
Silver Layer ELT Pipeline.

This script processes raw JSON data (typically from a Bronze layer), flattens 
nested structures using pandas, and loads it into a PostgreSQL database. It 
then executes a SQL transformation script to model the data into the Silver layer.
It features dynamic schema inference, transactional integrity (commit/rollback), 
and automatic file archiving upon success.
"""

import os
import json
import logging
import shutil
from pathlib import Path
import psycopg2
from dotenv import load_dotenv
import pandas as pd
import numpy as np

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
    
    # Paths (Using pathlib for robust, cross-platform path management)
    DATA_DIR = Path("data/markets")             # Source directory for incoming JSON files
    ARCHIVE_DIR = Path("data/archive")          # Destination for successfully processed files
    SQL_FILE_PATH = Path("sql/silver_transformation.sql") # SQL script for Silver layer logic
    LOG_DIR = Path("logs/silver_data")          # Directory for log files

def setup_logging():
    """Configures logging to write to both the console and a persistent log file."""
    # Ensure the log directory exists before attempting to write to it
    Config.LOG_DIR.mkdir(parents=True, exist_ok=True)
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(message)s",
        handlers=[
            logging.FileHandler(Config.LOG_DIR / "silver_pipeline.log"),
            logging.StreamHandler() # Also output to console for easy monitoring
        ]
    )

# ==========================================
# PIPELINE EXECUTION
# ==========================================
def load_json_files(conn) -> list:
    """
    Reads JSON files, flattens them, and inserts them into the silver layer database.
    Returns a list of successfully loaded file paths so they can be archived later.
    """
    logger = logging.getLogger(__name__)
    
    # Ensure the source directory exists to prevent FileNotFoundError
    Config.DATA_DIR.mkdir(parents=True, exist_ok=True)
    
    # Recursively find all JSON files in the data directory
    json_files = list(Config.DATA_DIR.rglob("*.json"))
    
    if not json_files:
        logger.info(f"No new JSON files found in {Config.DATA_DIR}.")
        return []

    processed_files = []
    
    # Use the existing database connection to create a cursor
    with conn.cursor() as cur:
        for file_path in json_files:
            try:
                # 1. Read and parse the raw JSON file
                with open(file_path, 'r') as f:
                    data = json.load(f)
                
                # 2. Flatten nested JSON into a structured DataFrame
                # json_normalize converts dictionaries like {"user": {"name": "X"}} into flat columns like "user.name"
                df = pd.json_normalize(data)
                
                df.columns = df.columns.str.replace('.', '_', regex=False)

                # Replace pandas NaN values with Python None so psycopg2 can insert correct SQL NULLs
                df = df.replace({np.nan: None})

                # Convert DataFrame rows into a list of tuples for efficient bulk insertion
                data_tuples = [tuple(row) for row in df.to_numpy()]
                
                # 3. Safely format column names 
                # Wrapping in double quotes is crucial here because json_normalize often creates 
                # column names with dots (e.g., 'user.name'), which breaks standard SQL syntax
                safe_columns = [f'"{col}"' for col in df.columns]
                columns_joined = ", ".join(safe_columns)
                
                # 4. Handle dynamic Table Creation (DDL)
                # Auto-generate schema based on the JSON keys, treating everything as TEXT for the staging step
                ddl_columns = ", ".join([f"{col} TEXT" for col in safe_columns])
                create_table_query = f"""
                    CREATE SCHEMA IF NOT EXISTS bronze;
                    CREATE TABLE IF NOT EXISTS bronze.markets (
                        {ddl_columns}
                    );
                """
                cur.execute(create_table_query)
                
                # 5. Handle Data Insertion (DML) using Parameterized Queries
                # Using %s placeholders protects against SQL injection and handles data type conversion safely
                placeholders = ", ".join(["%s"] * len(safe_columns)) 
                insert_query = f"""
                    INSERT INTO bronze.markets ({columns_joined})
                    VALUES ({placeholders});
                """
                
                # Bulk execute the insert statement for performance
                cur.executemany(insert_query, data_tuples)
                
                conn.commit()
                
                logger.info(f"Loaded {file_path.name} into bronze.markets.")
                processed_files.append(file_path)
                
            except json.JSONDecodeError as e:
                # Gracefully skip malformed files without crashing the whole pipeline
                logger.error(f"Invalid JSON in {file_path.name}. Skipping file. Error: {e}")
                
            except Exception as e:
                # Catching database-level issues. We raise the error here to trigger 
                # the transaction rollback in the main run_pipeline block.
                logger.error(f"Database error while loading {file_path.name}: {e}")
                raise e # Hard fail to trigger rollback
                
    return processed_files

def archive_files(files_to_archive: list):
    """Moves processed files to the archive directory to prevent re-processing."""
    logger = logging.getLogger(__name__)
    Config.ARCHIVE_DIR.mkdir(parents=True, exist_ok=True)
    
    for file_path in files_to_archive:
        try:
            destination = Config.ARCHIVE_DIR / file_path.name
            # If a file with the same name exists in archive, overwrite it to prevent a crash
            # This handles edge cases where a pipeline was rerun or file names collide
            if destination.exists():
                destination.unlink()
            
            # Physically move the file out of the source directory
            shutil.move(str(file_path), str(destination))
            logger.debug(f"Archived: {file_path.name}")
        except Exception as e:
            logger.error(f"Failed to archive {file_path.name}: {e}")

def run_pipeline():
    """Orchestrates loading JSON into silver, executing Silver ELT, and archiving."""
    logger = logging.getLogger(__name__)
    
    # Pre-flight checks: Ensure necessary configuration is present
    if not Config.DB_PASSWORD:
        logger.error("CRITICAL: DB_PASSWORD environment variable is missing.")
        return

    if not Config.SQL_FILE_PATH.exists():
        logger.error(f"CRITICAL: SQL file not found at {Config.SQL_FILE_PATH}")
        return
        
    connection_string = (
        f"host={Config.DB_HOST} port={Config.DB_PORT} dbname={Config.DB_NAME} "
        f"user={Config.DB_USER} password={Config.DB_PASSWORD}"
    )

    conn = None
    
    try:
        logger.info(f"Connecting to PostgreSQL database '{Config.DB_NAME}' at {Config.DB_HOST}...")
        conn = psycopg2.connect(connection_string)
        
        # 1. Extract & Load: Push all found files into the silver staging table
        logger.info("Starting silver layer loading phase...")
        processed_files = load_json_files(conn)
        
        if processed_files:
            # 2. Transform: Execute the Silver layer transformation SQL
            # This script typically contains the logic to clean, cast, and deduplicate the raw data
            logger.info(f"Executing Silver transformation from {Config.SQL_FILE_PATH}...")
            with conn.cursor() as cur:
                with open(Config.SQL_FILE_PATH, 'r') as sql_file:
                    transformation_sql = sql_file.read()
                
                cur.execute(transformation_sql)
                # Fetch rowcount (useful for observing how many records were affected by INSERT/UPDATE/DELETE)
                rows_affected = cur.rowcount 
            
            # 3. Commit: Save ALL changes permanently
            # By committing only at the very end, we treat the JSON load AND the SQL transform
            # as a single atomic transaction. Either everything succeeds, or nothing is saved.
            conn.commit()
            logger.info(f"Transformation successful. {rows_affected} rows affected in silver logic.")
            
            # 4. Clean up: Only archive files AFTER a successful database commit
            # This prevents us from archiving files if the database transaction failed
            archive_files(processed_files)
            logger.info(f"Successfully archived {len(processed_files)} processed files.")
            
        else:
            logger.info("No valid files were loaded. Skipping Silver transformation.")

    except psycopg2.Error as e:
        # Reverts both silver inserts and Silver transforms if any database operation fails
        if conn:
            conn.rollback() 
        logger.error(f"Database error occurred during execution: {e}")
        logger.error("Transaction rolled back. Files left in place for retry.")
    except Exception as e:
        # Catch-all for unexpected Python-level errors to ensure safety
        if conn:
            conn.rollback()
        logger.error(f"Unexpected application error: {e}")
        logger.error("Transaction rolled back. Files left in place for retry.")
    finally:
        # Always clean up the database connection, regardless of success or failure
        if conn:
            conn.close()
            logger.info("Database connection closed.")

# Standard idiom to execute logic only when the script is run directly
if __name__ == "__main__":
    setup_logging()
    logger = logging.getLogger(__name__) # Grab logger for main block
    logger.info("--- Starting ELT Pipeline ---")
    run_pipeline()
    logger.info("--- Pipeline Finished ---")