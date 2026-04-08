-- ==============================================================================
-- View: gold.tokenomics_analysis
-- Description: Calculates financial ratios and historical all-time peak/trough metrics.
-- Usage: Deep-dive financial analysis, finding "undervalued" tokens.
-- ==============================================================================

CREATE OR REPLACE VIEW gold.tokenomics_analysis AS
WITH latest_data AS (
    SELECT * FROM silver.markets 
    -- Quick subquery to get only the latest records without window functions
    WHERE (id, last_updated) IN (
        SELECT id, MAX(last_updated) FROM silver.markets GROUP BY id
    )
)
SELECT 
    id AS coin_id,
    symbol,
    current_price,
    market_cap,
    fully_diluted_valuation,
    
    -- TOKENOMICS: Market Cap to FDV Ratio. 
    -- A ratio of 1.0 means all coins are unlocked. 
    -- A ratio of 0.1 means 90% of coins are still locked (high future inflation risk).
    ROUND(
        (market_cap / NULLIF(fully_diluted_valuation, 0))::NUMERIC, 
        4
    ) AS mcap_to_fdv_ratio,
    
    -- All-Time Highs (ATH) Metrics
    ath AS all_time_high_price,
    ath_change_percentage AS drop_from_ath_pct,
    ath_date,
    -- Extract the number of days since the coin hit its peak
    EXTRACT(DAY FROM (CURRENT_TIMESTAMP - ath_date)) AS days_since_ath,
    
    -- All-Time Lows (ATL) Metrics
    atl AS all_time_low_price,
    atl_change_percentage AS gain_from_atl_pct,
    atl_date,
    EXTRACT(DAY FROM (CURRENT_TIMESTAMP - atl_date)) AS days_since_atl,
    
    -- ROI (Return on Investment) - Only applies to coins tracked since ICOs
    roi_percentage,
    roi_times,
    roi_currency

FROM latest_data
-- Filter out junk data where Market Cap isn't even established yet
WHERE market_cap IS NOT NULL AND market_cap > 0;
