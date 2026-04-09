#!/bin/bash
# ==============================================================================
# Script: entrypoint.sh
# Project: CoinFlow ELT Pipeline
# Description: Production-grade, environment-aware hourly scheduler.
# Features: Signal handling, Log rotation, Environment isolation.
# ==============================================================================

# set -e: Exit on error | -u: Error on unset vars | -o pipefail: Catch pipe errors
set -euo pipefail

# --- 1. Configuration & Paths ---
PROJECT_ROOT=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" &> /dev/null && pwd)
LOG_DIR="$PROJECT_ROOT/logs"
LOG_FILE="$LOG_DIR/entrypoint.log"
MAX_LOG_SIZE=10485760 # 10MB limit for rotation
SLEEP_INTERVAL=3600   # 1 hour

cd "$PROJECT_ROOT"
mkdir -p "$LOG_DIR"

# --- 2. Logging Setup (with Auto-Rotation) ---
# This function prevents the log file from growing infinitely
rotate_logs() {
    if [ -f "$LOG_FILE" ] && [ $(stat -c%s "$LOG_FILE") -gt $MAX_LOG_SIZE ]; then
        mv "$LOG_FILE" "${LOG_FILE}.old"
        echo "[$(date +'%Y-%m-%d %H:%M:%S')] 🔄 Log rotated." > "$LOG_FILE"
    fi
}

# Redirect all output to tee (terminal + file)
exec > >(tee -a "$LOG_FILE") 2>&1

# --- 3. Signal Handling (Graceful Shutdown) ---
# Allows Docker to stop the script properly (SIGTERM)
cleanup() {
    echo -e "\n[$(date +'%Y-%m-%d %H:%M:%S')] 🛑 Shutdown signal received. Cleaning up..."
    # Kill any background python processes if they exist
    jobs -p | xargs -r kill
    exit 0
}
trap cleanup SIGINT SIGTERM

# --- 4. Environment Bootstrapping ---
echo "[$(date +'%Y-%m-%d %H:%M:%S')] 🚀 Initializing CoinFlow Environment..."

if [ -f /.dockerenv ]; then
    echo "🐳 Mode: Docker Container"
else
    echo "💻 Mode: Local Machine"
    if [ -f .env ]; then
        echo "📥 Loading .env variables..."
        # Safely export variables, ignoring comments
        set -a; [ -f .env ] && . .env; set +a
    else
        echo "⚠️  No .env found. Falling back to system shell variables."
    fi
fi

# --- 5. Service Readiness Check ---
check_db() {
    local host="${DB_HOST:-localhost}"
    local port="${DB_PORT:-5432}"
    local user="${DB_USER:-postgres}"
    
    echo "🔍 Checking Database readiness at $host:$port..."
    for i in {1..15}; do
        if pg_isready -h "$host" -p "$port" -U "$user" > /dev/null 2>&1; then
            echo "✅ Database is online."
            return 0
        fi
        echo "⏳ Waiting for Database... ($i/15)"
        sleep 2
    done
    return 1
}

if ! check_db; then
    echo "❌ CRITICAL: Database connection failed. Exiting."
    exit 1
fi

# --- 6. Main Pipeline Loop ---
echo "⚙️  Starting Hourly Scheduler..."

while true; do
    rotate_logs
    
    START_TIME=$(date +%s)
    echo "======================================================================"
    echo "▶️  EXECUTION START: $(date)"
    echo "======================================================================"

    # Run layers sequentially. If one fails, the block stops but the loop continues.
    if (
        set -e
        echo "🔵 Layer 1: Bronze (Extraction)"
        python3 python/bronze_pipeline.py
        
        echo "⚪ Layer 2: Silver (Transformation)"
        python3 python/silver_pipeline.py
        
        echo "🟡 Layer 3: Gold (Analytics)"
        python3 python/gold_pipeline.py
    ); then
        END_TIME=$(date +%s)
        DURATION=$((END_TIME - START_TIME))
        echo "----------------------------------------------------------------------"
        echo "✅ SUCCESS: Pipeline completed in ${DURATION}s."
    else
        echo "----------------------------------------------------------------------"
        echo "❌ FAILURE: Pipeline crashed. Check logs above for tracebacks."
    fi

    echo "😴 Next run in 1 hour. (PID: $$)"
    sleep "$SLEEP_INTERVAL" & wait $!
done
