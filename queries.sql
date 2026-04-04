=============================================================================

-- HOW TO USE:
--   1. Make sure indexes.sql has been executed first.
--   2. Set the 30-day date window below (Step 1).
--   3. Run the queries one by one or source the whole file.
-- =============================================================================
  
-- Step 1: Check what dates are actually in your data
--         Run this first to confirm your data loaded correctly.
-- =============================================================================

SELECT
    MIN(event_timestamp) AS earliest_impression,
    MAX(event_timestamp) AS latest_impression,
    COUNT(*)             AS total_impressions
FROM impressions;


-- =============================================================================
-- Step 2: Set the 30-day analysis window
--         Run this once per session — all queries below use these variables.
-- =============================================================================

SET @start_date = '2024-01-01';
SET @end_date   = '2024-01-31';

-- =============================================================================
-- Q1 - How would an advertiser know which campaigns are the most effective in getting user engagement?
-- Campaign Performance: Retrieve the top 5 campaigns with the highest Click-Through Rate (CTR) over the 30 days period
--
-- How it works:
--   We LEFT JOIN impressions -> clicks so that impressions with no click
--   still appear in the result (with click_id = NULL).
--   COUNT(cl.click_id) counts only non-NULL values = total clicks.
--   CTR = clicks / impressions * 100, expressed as a percentage.
--
-- Index used: idx_imp_campaign_ts (campaign_id, event_timestamp)
-- =============================================================================

SELECT
    c.campaign_name,
    a.advertiser_name,
    COUNT(i.impression_id)                                        AS impressions,
    COUNT(cl.click_id)                                            AS clicks,
    ROUND(COUNT(cl.click_id) * 100.0 / COUNT(i.impression_id), 4) AS ctr_pct
FROM impressions i
JOIN campaigns   c  ON c.campaign_id   = i.campaign_id
JOIN advertisers a  ON a.advertiser_id = c.advertiser_id
LEFT JOIN clicks cl ON cl.impression_id = i.impression_id
WHERE i.event_timestamp BETWEEN @start_date AND @end_date
GROUP BY i.campaign_id, c.campaign_name, a.advertiser_name
HAVING COUNT(i.impression_id) > 0
ORDER BY ctr_pct DESC
LIMIT 5;


-- =============================================================================
-- 2. Which advertisers are the biggest spenders, and how does their spending correlate with engagement?
-- Advertiser Spending: Identify the advertisers that have spent the most money on ad impressions in the last month.
--
-- How it works:
--   Grouped by advertiser (across all their campaigns).
--   Spend  = SUM(impressions.ad_cost)
--   Revenue = SUM(clicks.ad_revenue)  — COALESCE turns NULL into 0
--   ROAS   = Revenue / Spend (> 1 means profitable, < 1 means losing money)
--   NULLIF protects against division by zero if a campaign has zero spend.
--
-- Index used: idx_imp_campaign_ts
-- =============================================================================

SELECT
    a.advertiser_name,
    COUNT(i.impression_id)                                              AS impressions,
    COUNT(cl.click_id)                                                  AS clicks,
    ROUND(COUNT(cl.click_id) * 100.0 / COUNT(i.impression_id), 4)      AS ctr_pct,
    ROUND(SUM(i.ad_cost), 2)                                            AS total_spend,
    ROUND(COALESCE(SUM(cl.ad_revenue), 0), 2)                          AS total_revenue,
    ROUND(
        COALESCE(SUM(cl.ad_revenue), 0) /
        NULLIF(SUM(i.ad_cost), 0),
    4)                                                                  AS roas
FROM impressions i
JOIN campaigns   c  ON c.campaign_id   = i.campaign_id
JOIN advertisers a  ON a.advertiser_id = c.advertiser_id
LEFT JOIN clicks cl ON cl.impression_id = i.impression_id
WHERE i.event_timestamp BETWEEN @start_date AND @end_date
GROUP BY a.advertiser_id, a.advertiser_name
ORDER BY total_spend DESC
LIMIT 10;


-- =============================================================================
-- 3. How efficiently is each campaign spending its budget relative to clicks and impressions?
-- Cost Efficiency: Calculate the average Cost Per Click (CPC) and Cost Per Mille (CPM) for each campaign.
--
-- Formulas:
--   CPC (Cost Per Click)      = total_spend / total_clicks
--   CPM (Cost Per Mille)      = total_spend / total_impressions * 1000
--
-- Notes:
--   NULLIF on clicks prevents division by zero for campaigns with 0 clicks
--   (CPC will be NULL for those — that's intentional and honest).
--   Ordered by CPC ascending: cheapest cost-per-click at the top.
--
-- Index used: idx_imp_campaign_ts
-- =============================================================================

SELECT
    c.campaign_name,
    a.advertiser_name,
    COUNT(i.impression_id)                                             AS impressions,
    COUNT(cl.click_id)                                                 AS clicks,
    ROUND(SUM(i.ad_cost), 2)                                          AS total_spend,
    ROUND(SUM(i.ad_cost) / NULLIF(COUNT(cl.click_id), 0), 4)          AS cpc,
    ROUND(SUM(i.ad_cost) * 1000.0 / COUNT(i.impression_id), 4)        AS cpm
FROM impressions i
JOIN campaigns   c  ON c.campaign_id   = i.campaign_id
JOIN advertisers a  ON a.advertiser_id = c.advertiser_id
LEFT JOIN clicks cl ON cl.impression_id = i.impression_id
WHERE i.event_timestamp BETWEEN @start_date AND @end_date
GROUP BY i.campaign_id, c.campaign_name, a.advertiser_name
HAVING COUNT(i.impression_id) > 0
ORDER BY cpc ASC;


-- =============================================================================
-- 4. In which countries or regions do ads generate the highest revenue, and where should advertisers focus their efforts?
-- Regional Analysis: Find the top-performing locations based on total ad revenue generated from clicks.
--
-- How it works:
--   We group by served_country_id on the impressions table — the country
--   where the ad was physically shown to the user.
--   Revenue only exists when a click happened (clicks.ad_revenue).
--   ROAS = revenue / spend per country.
--
-- Index used: idx_imp_country_ts (served_country_id, event_timestamp)
-- =============================================================================

SELECT
    co.country_name,
    COUNT(i.impression_id)                                             AS impressions,
    COUNT(cl.click_id)                                                 AS clicks,
    ROUND(COUNT(cl.click_id) * 100.0 / COUNT(i.impression_id), 4)     AS ctr_pct,
    ROUND(SUM(i.ad_cost), 2)                                          AS total_spend,
    ROUND(COALESCE(SUM(cl.ad_revenue), 0), 2)                         AS total_revenue,
    ROUND(
        COALESCE(SUM(cl.ad_revenue), 0) /
        NULLIF(SUM(i.ad_cost), 0),
    4)                                                                 AS roas
FROM impressions i
JOIN countries  co  ON co.country_id   = i.served_country_id
LEFT JOIN clicks cl ON cl.impression_id = i.impression_id
WHERE i.event_timestamp BETWEEN @start_date AND @end_date
GROUP BY i.served_country_id, co.country_name
ORDER BY total_revenue DESC
LIMIT 20;


-- =============================================================================
--- 5. Which users are the most engaged with advertising content?
-- User Engagement: Retrieve the top 10 users who have clicked on the most ads. 
--
-- How it works:
--   Engagement = number of clicks per user.
--   We join users and countries to get demographic data.
--   HAVING COUNT(cl.click_id) > 0 filters out users who had impressions
--   but never clicked — we only want active engagers.
--
-- Index used: idx_imp_user (user_id) + idx_imp_timestamp
-- =============================================================================

SELECT
    i.user_id,
    u.age,
    u.gender,
    co.country_name,
    COUNT(i.impression_id)                                              AS impressions_served,
    COUNT(cl.click_id)                                                  AS total_clicks,
    ROUND(COUNT(cl.click_id) * 100.0 / COUNT(i.impression_id), 4)      AS personal_ctr_pct
FROM impressions i
JOIN users      u   ON u.user_id    = i.user_id
JOIN countries  co  ON co.country_id = u.country_id
LEFT JOIN clicks cl ON cl.impression_id = i.impression_id
WHERE i.event_timestamp BETWEEN @start_date AND @end_date
GROUP BY i.user_id, u.age, u.gender, co.country_name
HAVING COUNT(cl.click_id) > 0
ORDER BY total_clicks DESC
LIMIT 10;


-- =============================================================================
-- 6. Which campaigns might need a budget increase to continue running effectively?
-- Budget Consumption: Identify campaigns that have spent more than 80% of their total budget and are close to exhausting their funds. 
--
-- IMPORTANT — hw1_fixed schema note:
--   The remaining_budget column was REMOVED from the campaigns table because
--   it is a derived value. We compute it here as:
--     remaining_budget = budget - SUM(impressions.ad_cost)
--
--   This query uses LIFETIME spend (not the 30-day window) because budget
--   is a lifetime metric — a campaign could have burned 80% of its budget
--   before January even started.
--
-- Index used: idx_imp_campaign_ts
-- =============================================================================
SELECT
    c.campaign_name,
    a.advertiser_name,
    c.campaign_start_date,
    c.campaign_end_date,
    ROUND(c.budget, 2)                                         AS budget,
    ROUND(COALESCE(SUM(i.ad_cost), 0), 2)                      AS total_spent,
    ROUND(c.budget - COALESCE(SUM(i.ad_cost), 0), 2)           AS remaining_budget,
    ROUND(COALESCE(SUM(i.ad_cost), 0) / c.budget * 100, 2)     AS pct_spent
FROM campaigns c
JOIN advertisers  a   ON a.advertiser_id  = c.advertiser_id
LEFT JOIN impressions i ON i.campaign_id  = c.campaign_id
GROUP BY
    c.campaign_id, c.campaign_name, a.advertiser_name,
    c.campaign_start_date, c.campaign_end_date, c.budget
HAVING pct_spent >= 80
ORDER BY pct_spent DESC;


-- =============================================================================
-- 7. Do certain types of ads perform better on mobile than desktop? How should advertisers adjust their strategies?
-- Device Performance Comparison: Compare CTR across different device types (mobile, desktop, tablet).
--
-- How it works:
--   GROUP BY impressions.device.
--   SUM(COUNT(*)) OVER () is a window function (MySQL 8.0+) that calculates
--   the grand total impressions across ALL device groups in one pass,
--   so we can express each device's share as a percentage of total.
--
-- Index used: idx_imp_device_ts (device, event_timestamp)
-- =============================================================================

SELECT
    i.device,
    COUNT(i.impression_id)                                              AS impressions,
    COUNT(cl.click_id)                                                  AS clicks,
    ROUND(COUNT(cl.click_id) * 100.0 / COUNT(i.impression_id), 4)      AS ctr_pct,
    ROUND(SUM(i.ad_cost), 2)                                            AS total_spend,
    ROUND(SUM(i.ad_cost) / NULLIF(COUNT(cl.click_id), 0), 4)           AS avg_cpc,
    ROUND(
        COUNT(i.impression_id) * 100.0 /
        SUM(COUNT(i.impression_id)) OVER (),
    2)                                                                  AS pct_of_total_impressions
FROM impressions i
LEFT JOIN clicks cl ON cl.impression_id = i.impression_id
WHERE i.event_timestamp BETWEEN @start_date AND @end_date
GROUP BY i.device
ORDER BY ctr_pct DESC;
