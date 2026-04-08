// Impressions by timestamp — for time-windowed queries (Tasks 2, 3)
db.user_engagements.createIndex(
  { "impressions.timestamp": 1 },
  { name: "idx_impressions_timestamp" }
)

// Impressions by campaign — for per-campaign aggregations (Task 3)
db.user_engagements.createIndex(
  { "impressions.campaign_id": 1 },
  { name: "idx_impressions_campaign" }
)

// Impressions by advertiser — for advertiser lookups (Task 3)
db.user_engagements.createIndex(
  { "impressions.advertiser_name": 1 },
  { name: "idx_impressions_advertiser" }
)

// Impressions by campaign name — for ad fatigue detection (Task 4)
db.user_engagements.createIndex(
  { "impressions.campaign_name": 1 },
  { name: "idx_impressions_campaign_name" }
)