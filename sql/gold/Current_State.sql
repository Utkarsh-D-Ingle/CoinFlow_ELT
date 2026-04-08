-- ==============================================================================
-- View: gold.current_market_snapshot
-- Description: Retrieves the absolute latest recorded data for each coin.
-- Usage: Live dashboards, current pricing widgets, and current rankings.
-- ==============================================================================

CREATE SCHEMA IF NOT EXISTS gold;

CREATE OR REPLACE VIEW gold.current_market_snapshot AS
WITH ranked_market_data AS (
    -- 1. Assign a row number to every record for each coin, ordered by the newest timestamp.
    -- rn = 1 will always be the most recently ingested row for that specific coin.
    SELECT 
        id,
        symbol,
        name,
        image,
        current_price,
        market_cap,
        market_cap_rank,
        total_volume,
        price_change_percentage_24h,
        market_cap_change_percentage_24h,
        circulating_supply,
        max_supply,
        last_updated,
        ROW_NUMBER() OVER (PARTITION BY id ORDER BY last_updated DESC) as rn
    FROM silver.markets
)
SELECT 
    id AS coin_id,
    symbol,
    name,
    image AS logo_url,
    current_price,
    market_cap,
    market_cap_rank,
    total_volume,
    price_change_percentage_24h,
    market_cap_change_percentage_24h,
    
    -- DEFENSIVE MATH: Calculate the percentage of max supply currently in circulation.
    -- NULLIF prevents 'division by zero' errors if a coin has 0 or NULL max_supply.
    ROUND(
        (circulating_supply / NULLIF(max_supply, 0) * 100)::NUMERIC, 
        2
    ) AS circulating_supply_pct,
    
    last_updated
FROM ranked_market_data
WHERE rn = 1; -- Filter down to only the latest snapshot
