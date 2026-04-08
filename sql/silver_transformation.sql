-- ==============================================================================
-- Schema Setup: Silver Layer
-- Purpose: Establish the 'silver' schema for cleansed, typed, and conformed data
-- ==============================================================================
CREATE SCHEMA IF NOT EXISTS silver;

-- ==============================================================================
-- Table: silver.markets
-- Purpose: Stores the latest snapshot of cryptocurrency market data.
-- Represents a structured, strictly-typed version of the raw Bronze data.
-- ==============================================================================
CREATE TABLE IF NOT EXISTS silver.markets (
    -- Primary Identifiers
    id VARCHAR(255) PRIMARY KEY,
    symbol VARCHAR(50),
    name VARCHAR(255),
    image TEXT,
    
    -- Current Pricing and Market Valuation
    current_price DOUBLE PRECISION,
    market_cap BIGINT,
    market_cap_rank INT,
    fully_diluted_valuation BIGINT,
    total_volume BIGINT,
    
    -- 24-Hour Performance Metrics
    high_24h DOUBLE PRECISION,
    low_24h DOUBLE PRECISION,
    price_change_24h DOUBLE PRECISION,
    price_change_percentage_24h DOUBLE PRECISION,
    market_cap_change_24h BIGINT,
    market_cap_change_percentage_24h DOUBLE PRECISION,
    
    -- Tokenomics / Supply Metrics
    circulating_supply DOUBLE PRECISION,
    total_supply DOUBLE PRECISION,
    max_supply DOUBLE PRECISION,
    
    -- All-Time High (ATH) Metrics
    ath DOUBLE PRECISION,
    ath_change_percentage DOUBLE PRECISION,
    ath_date TIMESTAMP,
    
    -- All-Time Low (ATL) Metrics
    atl DOUBLE PRECISION,
    atl_change_percentage DOUBLE PRECISION,
    atl_date TIMESTAMP,
    
    -- Return on Investment (ROI) Metrics (If applicable/available)
    roi_times DOUBLE PRECISION,
    roi_currency VARCHAR(50),
    roi_percentage DOUBLE PRECISION,
    
    -- Record Metadata
    last_updated TIMESTAMP
);

-- ==============================================================================
-- Data Pipeline: Bronze to Silver Load (UPSERT)
-- Purpose: Extracts the most recent records from the raw bronze table, 
--          casts them to strict data types, and updates the silver snapshot table.
-- ==============================================================================
INSERT INTO silver.markets (
    id, 
    symbol, 
    name, 
    image, 
    current_price, 
    market_cap, 
    market_cap_rank, 
    fully_diluted_valuation, 
    total_volume, 
    high_24h, 
    low_24h, 
    price_change_24h, 
    price_change_percentage_24h, 
    market_cap_change_24h, 
    market_cap_change_percentage_24h, 
    circulating_supply, 
    total_supply, 
    max_supply, 
    ath, 
    ath_change_percentage, 
    ath_date, 
    atl, 
    atl_change_percentage, 
    atl_date, 
    roi_times, 
    roi_currency, 
    roi_percentage, 
    last_updated
)
-- Deduplication Logic: 
-- DISTINCT ON guarantees only one row per 'id' is extracted from the Bronze batch.
-- This prevents primary key violations if the source contains duplicates.
SELECT DISTINCT ON (id)
    id, 
    symbol, 
    name, 
    image, 
    -- Data Type Casting: Converting raw (likely string/JSON) bronze data into strict Silver types.
    -- Note: Double casting (e.g., to NUMERIC then BIGINT) handles floating point strings safely before conversion to integers.
    CAST(current_price AS DOUBLE PRECISION), 
    CAST(CAST(market_cap AS NUMERIC) AS BIGINT), 
    CAST(CAST(market_cap_rank AS NUMERIC) AS INT), 
    CAST(CAST(fully_diluted_valuation AS NUMERIC) AS BIGINT), 
    CAST(CAST(total_volume AS NUMERIC) AS BIGINT), 
    CAST(high_24h AS DOUBLE PRECISION), 
    CAST(low_24h AS DOUBLE PRECISION), 
    CAST(price_change_24h AS DOUBLE PRECISION), 
    CAST(price_change_percentage_24h AS DOUBLE PRECISION), 
    CAST(CAST(market_cap_change_24h AS NUMERIC) AS BIGINT), 
    CAST(market_cap_change_percentage_24h AS DOUBLE PRECISION), 
    CAST(circulating_supply AS DOUBLE PRECISION), 
    CAST(total_supply AS DOUBLE PRECISION), 
    CAST(max_supply AS DOUBLE PRECISION), 
    CAST(ath AS DOUBLE PRECISION), 
    CAST(ath_change_percentage AS DOUBLE PRECISION), 
    CAST(ath_date AS TIMESTAMP), 
    CAST(atl AS DOUBLE PRECISION), 
    CAST(atl_change_percentage AS DOUBLE PRECISION), 
    CAST(atl_date AS TIMESTAMP), 
    CAST(roi_times AS DOUBLE PRECISION), 
    roi_currency, 
    CAST(roi_percentage AS DOUBLE PRECISION), 
    CAST(last_updated AS TIMESTAMP)
FROM bronze.markets
-- We order by last_updated descending alongside the DISTINCT ON (id) clause.
-- This ensures that if there are multiple records for the same coin in the Bronze batch, 
-- we only grab the freshest/most recent one.
ORDER BY id, CAST(last_updated AS TIMESTAMP) DESC

-- The UPSERT logic (SCD Type 1): 
-- If the 'id' already exists in the Silver table, overwrite the old data with the new data (EXCLUDED).
-- If it does not exist, it inserts as a new row.
ON CONFLICT (id) DO UPDATE SET
    symbol = EXCLUDED.symbol,
    name = EXCLUDED.name,
    image = EXCLUDED.image,
    current_price = EXCLUDED.current_price,
    market_cap = EXCLUDED.market_cap,
    market_cap_rank = EXCLUDED.market_cap_rank,
    fully_diluted_valuation = EXCLUDED.fully_diluted_valuation,
    total_volume = EXCLUDED.total_volume,
    high_24h = EXCLUDED.high_24h,
    low_24h = EXCLUDED.low_24h,
    price_change_24h = EXCLUDED.price_change_24h,
    price_change_percentage_24h = EXCLUDED.price_change_percentage_24h,
    market_cap_change_24h = EXCLUDED.market_cap_change_24h,
    market_cap_change_percentage_24h = EXCLUDED.market_cap_change_percentage_24h,
    circulating_supply = EXCLUDED.circulating_supply,
    total_supply = EXCLUDED.total_supply,
    max_supply = EXCLUDED.max_supply,
    ath = EXCLUDED.ath,
    ath_change_percentage = EXCLUDED.ath_change_percentage,
    ath_date = EXCLUDED.ath_date,
    atl = EXCLUDED.atl,
    atl_change_percentage = EXCLUDED.atl_change_percentage,
    atl_date = EXCLUDED.atl_date,
    roi_times = EXCLUDED.roi_times,
    roi_currency = EXCLUDED.roi_currency,
    roi_percentage = EXCLUDED.roi_percentage,
    last_updated = EXCLUDED.last_updated;