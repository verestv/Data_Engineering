=============================================================================

-- -----------------------------------------------------------------------------
-- Index 1: event_timestamp on impressions
--
-- WHY: Every single query in this homework has:
--        WHERE i.event_timestamp BETWEEN @start_date AND @end_date
--      Without this index MySQL reads all 10M rows to find January records.
--      With this index MySQL jumps directly to the relevant date range.
--
-- USED IN: Q1, Q2, Q3, Q4, Q5, Q7 (all windowed queries)
-- -----------------------------------------------------------------------------
CREATE INDEX idx_imp_timestamp
    ON impressions (event_timestamp);


-- -----------------------------------------------------------------------------
-- Index 2: (campaign_id, event_timestamp) on impressions — composite
--
-- WHY: Q1, Q2, Q3, Q6 all filter by date AND group/filter by campaign_id.
--      Pattern used in those queries:
--        WHERE  i.event_timestamp BETWEEN @start_date AND @end_date
--        GROUP BY i.campaign_id
--
--      A composite index on (campaign_id, event_timestamp) lets MySQL:
--        1. Locate all rows for a specific campaign using the first column.
--        2. Within those rows, apply the date range using the second column.
--      Both steps happen inside the index — MySQL never needs to touch the
--      actual table rows until it has already narrowed down to the exact match.
--
--      Two separate single-column indexes would be less efficient because
--      MySQL can only use one index at a time per table.
--
-- USED IN: Q1 (CTR per campaign), Q2 (spend per advertiser via campaign),
--          Q3 (CPC/CPM per campaign), Q6 (budget consumption)
-- -----------------------------------------------------------------------------
CREATE INDEX idx_imp_campaign_ts
    ON impressions (campaign_id, event_timestamp);


-- -----------------------------------------------------------------------------
-- Index 3: (device, event_timestamp) on impressions — composite
--
-- WHY: Q7 groups by device and filters by date:
--        WHERE  i.event_timestamp BETWEEN @start_date AND @end_date
--        GROUP BY i.device
--
--      Same pattern as Index 2 but for the device column.
--      The composite index lets MySQL find all impressions for a specific
--      device type within the date window without a full table scan.
--
-- USED IN: Q7 (CTR by device type)
-- -----------------------------------------------------------------------------
CREATE INDEX idx_imp_device_ts
    ON impressions (device, event_timestamp);


-- -----------------------------------------------------------------------------
-- Index 4: (served_country_id, event_timestamp) on impressions — composite
--
-- WHY: Q4 groups by country and filters by date:
--        WHERE  i.event_timestamp BETWEEN @start_date AND @end_date
--        GROUP BY i.served_country_id
--
--      Same pattern as Index 2 and 3 but for the country column.
--      Without this, MySQL scans all 10M rows to aggregate revenue per country.
--
-- USED IN: Q4 (top countries by ad revenue)
-- -----------------------------------------------------------------------------
CREATE INDEX idx_imp_country_ts
    ON impressions (served_country_id, event_timestamp);


-- -----------------------------------------------------------------------------
-- Index 5: user_id on impressions
--
-- WHY: Q5 groups all impressions by user_id to count clicks per user.
--      With 10M rows and potentially millions of unique users, grouping
--      without an index forces MySQL to sort the entire filtered result set
--      in memory before it can aggregate.
--      This index gives MySQL a pre-sorted structure so grouping is fast.
--
--      Note: only user_id here (not composite with event_timestamp) because
--      Q5 already narrows rows by date first (via idx_imp_timestamp),
--      then uses this index purely for the GROUP BY aggregation step.
--
-- USED IN: Q5 (top 10 most engaged users)
-- -----------------------------------------------------------------------------
CREATE INDEX idx_imp_user
    ON impressions (user_id);


-- -----------------------------------------------------------------------------
-- Index 6: impression_id on clicks
--
-- WHY: Every query joins impressions to clicks:
--        LEFT JOIN clicks cl ON cl.impression_id = i.impression_id
--
--      For each impression row returned by a query, MySQL must find the
--      matching click row (if any) in the clicks table (~1M rows).
--      Without an index on clicks.impression_id, MySQL scans the entire
--      clicks table for every single impression — this multiplies the cost
--      dramatically (10M impressions × 1M clicks lookup = extremely slow).
--
--      This index makes each lookup O(log n) instead of O(n).
--
--      A foreign key constraint exists on this column but MySQL does NOT
--      automatically create an index for FK columns — it must be done
--      explicitly, which is what this statement does.
--
-- USED IN: Q1, Q2, Q3, Q4, Q5, Q7 (all queries that join to clicks)
-- -----------------------------------------------------------------------------
CREATE INDEX idx_clicks_imp_id
    ON clicks (impression_id);
