# 🌊 CoinFlow: Cryptocurrency ELT Data Pipeline

[![Python](https://img.shields.io/badge/Python-3.10+-blue.svg)](https://www.python.org/)
[![PostgreSQL](https://img.shields.io/badge/PostgreSQL-15.0+-blue.svg)](https://www.postgresql.org/)
[![Docker](https://img.shields.io/badge/Docker-Supported-blue.svg)](https://www.docker.com/)
[![Architecture](https://img.shields.io/badge/Architecture-Medallion-orange.svg)]()

## 📌 Project Overview
CoinFlow is an automated ELT (Extract, Load, Transform) data pipeline designed to ingest real-time cryptocurrency market data from the CoinGecko API. 

This project leverages the **Medallion Architecture** (Bronze, Silver, Gold). It extracts raw JSON payloads locally, flattens them using Pandas, and loads them into a PostgreSQL staging table as raw text. From there, it relies entirely on native, highly optimized SQL queries to clean, cast data types, and aggregate the data into business-ready reporting metrics.

## 🏗️ Architecture & Data Flow

CoinFlow strictly follows an ELT pattern, transitioning data systematically through landing zones and database schemas:

1. **Extraction (Local Landing):** The `bronze_pipeline.py` script manages API pagination and rate limiting, extracting raw data from the CoinGecko API and saving it securely as local `.json` files.
2. **Bronze Layer (Raw Staging):** The `silver_pipeline.py` script picks up via a `load_json` function. It reads the local JSON files, uses `pandas` to flatten and normalize the nested structures, and loads the data into the `bronze.markets` PostgreSQL table. At this stage, to prevent schema-on-write errors, **all fields are strictly loaded as `text` datatypes**.
3. **Silver Layer (Cleansed & Conformed):** The `silver_transformation.sql` script processes the `bronze.markets` text table. It safely casts the text fields into their proper native SQL types (e.g., `NUMERIC`, `TIMESTAMP WITH TIME ZONE`), handles missing values, filters out corrupt records, and inserts the clean data into the `silver.markets` table to act as the Single Source of Truth.
4. **Gold Layer (Business Logic):** Finally, `gold_pipeline.py` executes SQL scripts from the `sql/gold` directory. This generates Materialized Views and dynamic Views that aggregate the Silver data into dashboards-ready metrics (e.g., daily historical performance, top market movers).

## 🚀 Key Features
* **Medallion Architecture:** Clear separation of concerns between raw ingested text (Bronze), cleansed Single Source of Truth (Silver), and business-level aggregations (Gold).
* **Hybrid Python/SQL ELT:** Utilizes `pandas` for handling messy, nested JSON structures in memory, and utilizes PostgreSQL's compute engine for heavy type-casting and aggregations.
* **Idempotent Executions:** File archiving and `ON CONFLICT` database constraints ensure the pipeline can be run multiple times without duplicating data.
* **Flexible Execution:** Can be run natively on a local machine via shell scripts or fully containerized via Docker.

## 🛠️ Tech Stack
* **Orchestration:** Python, Docker, Bash
* **Data Processing:** `pandas` (JSON flattening/normalization)
* **Database & Transformation Engine:** PostgreSQL (utilizing CTEs, safe type casting, and Materialized Views)
* **Libraries:** `pandas`, `psycopg2-binary`, `requests`, `python-dotenv`
* **Data Source:** [CoinGecko API (Demo Tier)](https://docs.coingecko.com/)

## 📂 Repository Structure

Coinflow/
├── data/                               # Local storage for data processing
│   ├── archive/                        # Backups of processed files (e.g., 21.json)
│   └── markets/                        # Partitioned raw data landing zone
│       └── date=2026-04-08/
│           ├── 22.json                 # Unprocessed API JSON payload
│           └── _SUCCESS_21             # Marker indicating successful processing
│
├── logs/                               # Execution logs organized by pipeline layer
│   ├── bronze_data/
│   │   └── bronze_pipeline.log
│   ├── silver/
│   │   └── silver_pipeline.log
│   └── gold/
│       └── gold_pipeline.log
│
├── python/                             # Python orchestration scripts
│   ├── bronze_pipeline.py              # API extraction and local JSON saving
│   ├── silver_pipeline.py              # Pandas normalization & triggering Silver SQL
│   └── gold_pipeline.py                # Business logic DDL & MatView refreshes
│
├── sql/                                # Database queries and logic
│   ├── silver_transformation.sql       # Casts Bronze text table into Silver typed table
│   └── gold/                           # BI Views and Materialized Views
│       ├── Current_State.sql
│       ├── Daily_Market_Performance.sql
│       ├── Market_Mover_24H.sql
│       └── Tokenomics_Analysis.sql
│
├── .env                                # Local environment variables (ignored by git)
├── docker-compose.yml                  # Docker services orchestration (App + DB)
├── dockerfile                          # Python environment image builder
├── entrypoint.sh                       # Startup and pipeline execution script
└── requirements.txt                    # Python library dependencies

## ⚙️ Getting Started
### Prerequisites
 * Python 3.10+ and PostgreSQL (if running locally)
 * Docker & Docker Compose (if using containers)
 * A free CoinGecko Demo API Key
### 1. Clone the Repository
```bash
git clone [https://github.com/yourusername/CoinFlow.git](https://github.com/yourusername/CoinFlow.git)
cd CoinFlow

```
### 2. Configure Environment Variables
Create a .env file in the root directory. Paste the following configuration, ensuring you add your actual API key.
```env
# ==========================================
# CoinFlow ELT Pipeline Configuration
# ==========================================

# ------------------------------------------
# PostgreSQL Database Credentials
# ------------------------------------------
# If using Docker Compose, DB_HOST should be the service name (postgres_db)
# If running locally without Docker, use localhost
DB_HOST=postgres_db
DB_PORT=5432
DB_NAME=CoinFlow_db
DB_USER=CoinFlow_Admin
DB_PASSWORD=coinflow123

# ------------------------------------------
# API Configuration
# ------------------------------------------
# Replace with your actual CoinGecko Demo API Key
COINGECKO_API_KEY=Your_CoinGecko_API_Key

# ------------------------------------------
# Pipeline Configurations
# ------------------------------------------
# Number of pages to fetch from the API (Max 250 coins per page)
CG_MAX_PAGES=2

```
### 3. Run the Pipeline
You have two options to execute the CoinFlow pipeline: via Docker (Recommended) or directly via the shell script.
#### Option A: Using Docker Compose (Recommended)
This option automatically spins up a PostgreSQL database, configures the schemas, builds the Python environment, and runs the pipeline sequentially.
 1. Ensure Docker is running on your machine.
 2. Execute the build and up command:
     
```bash
   docker-compose up --build
```

#### Option B: Direct Local Execution
If you already have a local PostgreSQL server running and prefer not to use Docker, you can run the pipeline directly on your machine.
 1. Update your .env file so that DB_HOST=localhost.
 2. Install the required Python dependencies:
     
```bash
   pip install -r requirements.txt
   
```

 3. Make the orchestrator script executable and run it:
     
```bash
   chmod +x entrypoint.sh
   ./entrypoint.sh
   
```

## 📊 Analytics & Downstream BI
Once the entrypoint.sh script completes its run, the transformed data is ready for analysis.
Connect your preferred business intelligence tool (such as **Power BI**, **Tableau**, or **Metabase**) directly to the PostgreSQL database exposed on port 5432.
Query the gold schema directly to access pre-calculated, highly optimized reporting views:
 * **gold.current_market_snapshot**: Real-time pricing and deduplicated market rankings.
 * **gold.daily_market_performance**: Aggregated time-series facts for candlestick charts and moving averages.
 * **gold.market_movers_24h**: Filtered top gainers and losers backed by volume gates.
 * **gold.tokenomics_analysis**: Market Cap to Fully Diluted Valuation (FDV) ratios and all-time-high drops.
## 🤝 Contributions
Feel free to submit issues or pull requests. For major changes, please open an issue first to discuss the proposed updates.
## 📝 License
This project is licensed under the MIT License.
