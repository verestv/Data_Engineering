-- ============================================================
-- HW4: Cassandra Schema for Ad Event Data
-- Drop + recreate keyspace and all 5 query-optimized tables
-- ============================================================

-- To DROP everything and start fresh (run this manually):
--   DROP KEYSPACE IF EXISTS adtech;
-- Then re-run this file.

CREATE KEYSPACE IF NOT EXISTS adtech
WITH REPLICATION = {
  'class': 'SimpleStrategy',
  'replication_factor': 1
};

USE adtech;

-- ============================================================
-- TABLE 1: campaign_daily_stats
-- Query 1: CTR per campaign per day
--
-- Source columns used:
--   impressions.csv → impression_id, campaign_id, event_timestamp, ad_cost
--   campaigns.csv   → campaign_name
--   advertisers.csv → advertiser_name
--   clicks.csv      → click_id (count per impression_id = click happened)
--
-- Partition key  : campaign_id  (one partition per campaign)
-- Clustering key : event_date DESC (latest day first)
-- ============================================================
CREATE TABLE IF NOT EXISTS campaign_daily_stats (
    campaign_id       BIGINT,
    event_date        DATE,
    campaign_name     TEXT,
    advertiser_name   TEXT,
    total_impressions BIGINT,
    total_clicks      BIGINT,
    total_cost        DECIMAL,
    ctr               DOUBLE,
    PRIMARY KEY (campaign_id, event_date)
) WITH CLUSTERING ORDER BY (event_date DESC);


-- ============================================================
-- TABLE 2: advertiser_spend_by_day
-- Query 2: Top 5 advertisers by total spend (last 30 days)
--
-- Source columns used:
--   impressions.csv → ad_cost, event_timestamp, campaign_id
--   campaigns.csv   → advertiser_id
--   advertisers.csv → advertiser_name
--
-- Partition key  : (bucket, advertiser_id)  bucket=1 keeps global
-- Clustering key : event_date DESC
-- Top-N aggregation done in Python after fetching 30-day window
-- ============================================================
CREATE TABLE IF NOT EXISTS advertiser_spend_by_day (
    bucket          INT,
    advertiser_id   BIGINT,
    event_date      DATE,
    advertiser_name TEXT,
    daily_spend     DECIMAL,
    PRIMARY KEY ((bucket, advertiser_id), event_date)
) WITH CLUSTERING ORDER BY (event_date DESC);


-- ============================================================
-- TABLE 3: user_ad_history
-- Query 3: Last 10 ads seen by a UserID (+ was it clicked)
--
-- Source columns used:
--   impressions.csv → impression_id, user_id, campaign_id,
--                     ad_slot_size, device, event_timestamp, ad_cost
--   clicks.csv      → click_id, click_timestamp, ad_revenue
--                     (joined via impression_id)
--   campaigns.csv   → campaign_name
--   advertisers.csv → advertiser_name
--
-- Partition key  : user_id
-- Clustering key : event_timestamp DESC, impression_id ASC
--   → LIMIT 10 returns the 10 most recent impressions for that user
-- ============================================================
CREATE TABLE IF NOT EXISTS user_ad_history (
    user_id           BIGINT,
    event_timestamp   TIMESTAMP,
    impression_id     TEXT,
    campaign_id       BIGINT,
    campaign_name     TEXT,
    advertiser_name   TEXT,
    ad_slot_size      TEXT,
    device            TEXT,
    was_clicked       BOOLEAN,
    click_timestamp   TIMESTAMP,
    ad_revenue        DECIMAL,
    ad_cost           DECIMAL,
    PRIMARY KEY (user_id, event_timestamp, impression_id)
) WITH CLUSTERING ORDER BY (event_timestamp DESC, impression_id ASC);


-- ============================================================
-- TABLE 4: user_click_counts
-- Query 4: Top 10 most active users by click count (last 30 days)
--
-- Source columns used:
--   clicks.csv      → click_id, impression_id
--   impressions.csv → user_id, event_timestamp (joined via impression_id)
--
-- Partition key  : (bucket, user_id)  bucket=1 global leaderboard
-- Clustering key : event_date DESC
-- Top-N done in Python
-- ============================================================
CREATE TABLE IF NOT EXISTS user_click_counts (
    bucket      INT,
    user_id     BIGINT,
    event_date  DATE,
    click_count BIGINT,
    PRIMARY KEY ((bucket, user_id), event_date)
) WITH CLUSTERING ORDER BY (event_date DESC);


-- ============================================================
-- TABLE 5: advertiser_spend_by_region
-- Query 5: Top 5 advertisers by spend in a specific country (last 30 days)
--
-- Source columns used:
--   impressions.csv → ad_cost, event_timestamp, campaign_id, served_country_id
--   countries.csv   → country_name  (resolved from served_country_id)
--   campaigns.csv   → advertiser_id
--   advertisers.csv → advertiser_name
--
-- Partition key  : (country_name, advertiser_id)
--   → one partition per country+advertiser combo, efficient country-scoped scan
-- Clustering key : event_date DESC
-- ============================================================
CREATE TABLE IF NOT EXISTS advertiser_spend_by_region (
    country_name    TEXT,
    advertiser_id   BIGINT,
    event_date      DATE,
    advertiser_name TEXT,
    daily_spend     DECIMAL,
    PRIMARY KEY ((country_name, advertiser_id), event_date)
) WITH CLUSTERING ORDER BY (event_date DESC);