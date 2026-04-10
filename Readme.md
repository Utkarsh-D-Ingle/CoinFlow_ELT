# CoinFlow: End-to-End ELT Data Pipeline (Production-Inspired Design)

[![Python](https://img.shields.io/badge/Python-3.10+-blue.svg)](https://www.python.org/)
[![PostgreSQL](https://img.shields.io/badge/PostgreSQL-15.0+-blue.svg)](https://www.postgresql.org/)
[![Docker](https://img.shields.io/badge/Docker-Supported-blue.svg)](https://www.docker.com/)
[![Architecture](https://img.shields.io/badge/Architecture-Medallion-orange.svg)]()

## TL;DR

CoinFlow is an end-to-end ELT pipeline that:
- Extracts cryptocurrency market data from an API  
- Cleans and transforms it using SQL  
- Produces analytics-ready datasets for reporting  

Built using **Python, PostgreSQL, and Docker**, it demonstrates how real-world data pipelines are structured using a **Medallion Architecture (Bronze → Silver → Gold)**.

---

## 📌 Project Overview
CoinFlow is a **containerized ELT pipeline** designed to simulate production-style data systems.

Instead of focusing only on *what the data is*, this project focuses on:
- Reliable data ingestion  
- Scalable transformations  
- Clean data modeling for analytics  

The pipeline ingests real-time cryptocurrency data from the CoinGecko API and processes it into structured, analysis-ready datasets.

---

## 🧱 Architecture: Medallion Design

The pipeline follows a **layered architecture** inside PostgreSQL:

### 🥉 Bronze Layer (Raw Ingestion)
- Python-based ingestion handling:
  - API pagination  
  - Rate limiting  
- Stores raw data in PostgreSQL as `TEXT`  
- Prevents failures due to schema changes  

---

### 🥈 Silver Layer (Data Cleaning & Normalization)
- Implemented using **SQL (CTEs, constraints, ON CONFLICT)**  
- Handles:
  - Type casting  
  - Missing values  
  - Deduplication  

✅ Ensures **idempotency** → safe to re-run without duplicate data  

---

### 🥇 Gold Layer (Analytics & Modeling)
- Builds **materialized views** for analytics  
- Uses **window functions and aggregations**

Example outputs:
- Market trends and rankings  
- Top gainers/losers (24h)  
- Token risk metrics (FDV vs Market Cap)  

---

## ⚙️ Engineering Highlights

### 🔄 Orchestration
- Single entry point using `entrypoint.sh`  
- Handles task sequencing and dependencies  

### 📦 Containerization
- Fully containerized using **Docker & Docker Compose**  
- Ensures consistent execution across environments  

### 📊 Observability
- Logging across Python and SQL layers  
- Enables traceability for each pipeline run  

### 🛡️ Data Reliability
- Handles API inconsistencies and missing values  
- Designed for robustness and repeatability  

---

## 🛠️ Tech Stack

**Languages & Processing**
- Python  
- SQL  

**Database**
- PostgreSQL (CTEs, Materialized Views, Schemas)

**Infrastructure**
- Docker  
- Docker Compose  
- Bash  

**Data Source**
- CoinGecko API  

---

## 📊 Example Analytics Use Cases

After pipeline execution, the **Gold layer** can be used for:

- 📈 Market trend analysis  
- 🚀 Top performing tokens (24h)  
- ⚠️ Risk indicators (FDV vs Market Cap)  
- 📉 Volatility tracking  

---

## 📂 Repository Structure

```markdown
Coinflow/
├── python/                # Pipeline scripts
├── sql/                   # SQL transformations & models
├── docker-compose.yml     # Container orchestration
├── dockerfile             # Python environment
├── entrypoint.sh          # Pipeline runner
└── requirements.txt       # Dependencies              # Python library dependencies
```

## ⚙️ Getting Started
### Prerequisites
 * Python 3.10+ and PostgreSQL (if running locally)
 * Docker & Docker Compose (if using containers)
 * A free CoinGecko Demo API Key
### 1. Clone the Repository
```bash
git clone https://github.com/Utkarsh-D-Ingle/CoinFlow.git
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

### Option B: Direct Local Execution
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

## 📊 Using the Data
After execution, connect any BI tool to PostgreSQL:
    Power BI
    Tableau
    Metabase
Query the Gold layer for ready-to-use datasets:
**gold.current_market_snapshot**
**gold.daily_market_performance**
**gold.market_movers_24h**
**gold.tokenomics_analysis**

## 🤝 Contributions
Feel free to submit issues or pull requests. For major changes, please open an issue first to discuss the proposed updates.
## 📝 License
This project is licensed under the MIT License.
