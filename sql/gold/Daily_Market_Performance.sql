-- ==============================================================================
-- Materialized View: gold.daily_market_performance
-- Description: Aggregates intra-day price/volume snapshots into daily historical facts.
-- Usage: Time-series charts (Candlesticks, moving averages, volume trends over time).
-- ==============================================================================

CREATE MATERIALIZED VIEW IF NOT EXISTS gold.daily_market_performance AS
SELECT 
    id AS coin_id,
    symbol,
    name,
    DATE(last_updated) AS trade_date,
    
    -- Price Aggregations
    ROUND(CAST(AVG(current_price) AS NUMERIC), 8) AS avg_daily_price,
    MAX(current_price) AS max_daily_price,
    MIN(current_price) AS min_daily_price,
    
    -- The difference between the highest and lowest reported price that day (Volatility)
    MAX(high_24h) - MIN(low_24h) AS intraday_volatility_spread,
    
    -- Volume & Market Cap Aggregations
    -- Since we might poll multiple times a day, AVG gives the best daily representation
    ROUND(AVG(total_volume), 2) AS avg_daily_volume,
    ROUND(AVG(market_cap), 2) AS avg_daily_market_cap,
    
    -- Data Quality Metric: Tracks how many times we successfully polled this coin today
    COUNT(*) AS data_points_collected
FROM silver.markets
GROUP BY 
    id, 
    symbol, 
    name, 
    DATE(last_updated)
WITH DATA;

-- ==============================================================================
-- Indexes for Materialized View
-- Description: Crucial for production performance. Allows lightning-fast time-series 
-- lookups and enables the "CONCURRENTLY" refresh method in PostgreSQL.
-- ==============================================================================
CREATE UNIQUE INDEX IF NOT EXISTS idx_gold_daily_perf_unique 
    ON gold.daily_market_performance(coin_id, trade_date);

CREATE INDEX IF NOT EXISTS idx_gold_daily_perf_date 
    ON gold.daily_market_performance(trade_date DESC);
