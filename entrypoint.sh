#!/bin/bash
# ==============================================================================
# Script: entrypoint.sh
# Description: Docker entrypoint for the CoinFlow ELT pipeline.
# ==============================================================================
set -euo pipefail

echo "[$(date +'%Y-%m-%d %H:%M:%S')] Starting Dockerized CoinFlow Pipeline..."

# 1. Wait for PostgreSQL to be ready
echo "Waiting for PostgreSQL at $DB_HOST:$DB_PORT..."
TIMEOUT=30
until pg_isready -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" > /dev/null 2>&1 || [ $TIMEOUT -eq 0 ]; do
    echo -n "."
    sleep 2
    ((TIMEOUT--))
done
echo ""

if [ $TIMEOUT -eq 0 ]; then
    echo "❌ CRITICAL: Database is unreachable. Exiting container."
    exit 1
fi
echo "✅ Database is online."

# 2. Execute Pipeline
echo "--- Executing Bronze Layer ---"
python3 python/bronze_pipeline.py

echo "--- Executing Silver Layer ---"
python3 python/silver_pipeline.py

echo "--- Executing Gold Layer ---"
python3 python/gold_pipeline.py

echo "🎉 Pipeline Executed Successfully!"