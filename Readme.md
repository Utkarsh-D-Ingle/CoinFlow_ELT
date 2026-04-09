# 🌊 CoinFlow: Enterprise-Grade ELT Data Pipeline

[![Python](https://img.shields.io/badge/Python-3.10+-blue.svg)](https://www.python.org/)
[![PostgreSQL](https://img.shields.io/badge/PostgreSQL-15.0+-blue.svg)](https://www.postgresql.org/)
[![Docker](https://img.shields.io/badge/Docker-Supported-blue.svg)](https://www.docker.com/)
[![Architecture](https://img.shields.io/badge/Architecture-Medallion-orange.svg)]()

## 📌 Project Overview
CoinFlow is a custom, containerized ELT (Extract, Load, Transform) framework designed to mirror production-level data lakehouse principles. Moving beyond basic API scripts, this project implements a resilient **Medallion Architecture** to ingest, normalize, and model real-time cryptocurrency market data from the CoinGecko API.

The project is engineered with a focus on **Idempotency**, **Defensive Schema Design**, and **Environment Isolation**, providing a warehouse-agnostic blueprint for scalable data infrastructure.

## 🏗️ Architecture & Engineering Rigor

CoinFlow leverages an ELT paradigm, utilizing PostgreSQL as a high-performance compute engine for transformation logic rather than relying on fragile in-memory processing.

1. **Extraction (Local Landing):** The `bronze_pipeline.py` script manages complex API pagination and rate-limiting. Extracted JSON payloads are persisted locally to ensure a "replayable" data source.
2. **Bronze Layer (Raw Staging):** Data is ingested into the `bronze.markets` table. To prevent **Schema-on-Write** failures from upstream API changes, all fields are strictly loaded as `TEXT`.
3. **Silver Layer (Normalization & Quality):** `silver_transformation.sql` performs the heavy lifting. Using SQL CTEs, it handles type-casting, null-value reconciliation, and deduplication. Strict SQL constraints and `ON CONFLICT` logic guarantee **Idempotency**—the pipeline can be executed infinitely without data duplication.
4. **Gold Layer (Analytics & Modeling):** `gold_pipeline.py` automates DDL scripts to generate Materialized Views. This layer calculates business-ready narratives like FDV-to-Market Cap ratios and volatility spreads via advanced window functions.

## 🚀 Key Engineering Features

* **Custom Orchestration:** The entire lifecycle is managed by a single `entrypoint.sh` Bash orchestrator, handling task sequencing and dependency management.
* **Unified Logging & Observability:** Integrated logging across Python and SQL layers provides a clear audit trail for every execution.
* **Containerized Parity:** Full Dockerization ensures the pipeline runs identically on a local developer machine as it would on a cloud-based EC2 or Kubernetes instance.
* **Defensive Design:** Implements robust handling for inconsistent data, missing fields, and API anomalies to ensure pipeline uptime.

## 🛠️ Tech Stack
* **Orchestration:** Bash, Docker, Docker Compose
* **Compute & Storage:** PostgreSQL 15+ (CTEs, Materialized Views, Schemas)
* **Data Processing:** Python 3.10, Pandas (for JSON flattening)
* **Data Source:** [CoinGecko API](https://www.coingecko.com/en/api)

## 📂 Repository Structure

```markdown
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
```

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
