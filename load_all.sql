USE adtech_db;

SET FOREIGN_KEY_CHECKS = 0;

-- 1. Countries
LOAD DATA INFILE '/var/lib/mysql-files/countries.csv'
INTO TABLE countries
FIELDS TERMINATED BY ','
OPTIONALLY ENCLOSED BY '"'
LINES TERMINATED BY '\n'
IGNORE 1 LINES
(country_id, country_name);

-- 2. Interests
LOAD DATA INFILE '/var/lib/mysql-files/interests.csv'
INTO TABLE interests
FIELDS TERMINATED BY ','
OPTIONALLY ENCLOSED BY '"'
LINES TERMINATED BY '\n'
IGNORE 1 LINES
(interest_id, interest_name);

-- 3. Advertisers
LOAD DATA INFILE '/var/lib/mysql-files/advertisers.csv'
INTO TABLE advertisers
FIELDS TERMINATED BY ','
OPTIONALLY ENCLOSED BY '"'
LINES TERMINATED BY '\n'
IGNORE 1 LINES
(advertiser_id, advertiser_name);

-- 4. Users
LOAD DATA INFILE '/var/lib/mysql-files/users_fact.csv'
INTO TABLE users
FIELDS TERMINATED BY ','
OPTIONALLY ENCLOSED BY '"'
LINES TERMINATED BY '\n'
IGNORE 1 LINES
(user_id, age, gender, country_id, signup_date);

-- 5. User interests
LOAD DATA INFILE '/var/lib/mysql-files/user_interests.csv'
INTO TABLE user_interests
FIELDS TERMINATED BY ','
OPTIONALLY ENCLOSED BY '"'
LINES TERMINATED BY '\n'
IGNORE 1 LINES
(user_id, interest_id);

-- 6. Campaigns
LOAD DATA INFILE '/var/lib/mysql-files/campaigns.csv'
INTO TABLE campaigns
FIELDS TERMINATED BY ','
OPTIONALLY ENCLOSED BY '"'
LINES TERMINATED BY '\n'
IGNORE 1 LINES
(campaign_id, advertiser_id, campaign_name,
 campaign_start_date, campaign_end_date,
 budget, remaining_budget);

-- 7. Campaign targeting
LOAD DATA INFILE '/var/lib/mysql-files/campaign_targeting.csv'
INTO TABLE campaign_targeting
FIELDS TERMINATED BY ','
OPTIONALLY ENCLOSED BY '"'
LINES TERMINATED BY '\n'
IGNORE 1 LINES
(campaign_id, targeting_criteria, target_interest_id, target_country_id);

-- 8. Ad events
LOAD DATA INFILE '/var/lib/mysql-files/ad_events.csv'
INTO TABLE ad_events
FIELDS TERMINATED BY ','
OPTIONALLY ENCLOSED BY '"'
LINES TERMINATED BY '\n'
IGNORE 1 LINES
(
  event_id,
  campaign_id,
  user_id,
  ad_slot_size,
  device,
  served_country_id,
  event_timestamp,
  bid_amount,
  ad_cost,
  @was_clicked_str,
  @click_ts_str,
  ad_revenue
)
SET was_clicked = CASE
        WHEN @was_clicked_str = 'True'  THEN 1
        WHEN @was_clicked_str = 'False' THEN 0
        ELSE NULL
    END,
    click_timestamp = NULLIF(@click_ts_str, '');


SET FOREIGN_KEY_CHECKS = 1;
