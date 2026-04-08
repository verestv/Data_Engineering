db.user_engagements.createIndex({ "impressions.timestamp": 1 }, { name: "idx_impressions_timestamp" })
db.user_engagements.createIndex({ "impressions.campaign_id": 1 }, { name: "idx_impressions_campaign" })
db.user_engagements.createIndex({ "impressions.advertiser_name": 1 }, { name: "idx_impressions_advertiser" })
db.user_engagements.createIndex({ "impressions.campaign_name": 1 }, { name: "idx_impressions_campaign_name" })