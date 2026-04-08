-- ==============================================================================
-- View: gold.market_movers_24h
-- Description: Categorizes and ranks coins based on 24-hour momentum and volatility.
-- Usage: Front-page dashboard widgets ("Top Gainers", "Top Losers").
-- ==============================================================================

CREATE OR REPLACE VIEW gold.market_movers_24h AS
WITH latest_data AS (
    SELECT * FROM silver.markets 
    WHERE (id, last_updated) IN (
        SELECT id, MAX(last_updated) FROM silver.markets GROUP BY id
    )
)
SELECT 
    id AS coin_id,
    symbol,
    name,
    current_price,
    market_cap_rank,
    price_change_percentage_24h,
    market_cap_change_24h,
    total_volume,
    
    -- BUSINESS LOGIC: Categorize the 24-hour momentum for easy BI tool color-coding
    CASE 
        WHEN price_change_percentage_24h >= 15 THEN 'Extreme Surge (>= 15%)'
        WHEN price_change_percentage_24h >= 5  THEN 'Strong Gain (5% to 15%)'
        WHEN price_change_percentage_24h > 0   THEN 'Slight Gain (0% to 5%)'
        WHEN price_change_percentage_24h <= -15 THEN 'Extreme Crash (<= -15%)'
        WHEN price_change_percentage_24h <= -5  THEN 'Strong Drop (-5% to -15%)'
        WHEN price_change_percentage_24h < 0   THEN 'Slight Drop (0% to -5%)'
        ELSE 'Flat'
    END AS momentum_category

FROM latest_data
WHERE 
    price_change_percentage_24h IS NOT NULL 
    -- QUALITY GATE: Ignore dead or unranked coins
    AND market_cap_rank IS NOT NULL 
    -- QUALITY GATE: Only consider the top 1000 coins to filter out illiquid token manipulation
    AND market_cap_rank <= 1000
    -- QUALITY GATE: Ensure there is actual trading volume backing the price movement
    AND total_volume > 100000 
ORDER BY 
    price_change_percentage_24h DESC;
