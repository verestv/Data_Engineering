USE adtech_db;

SET FOREIGN_KEY_CHECKS = 0;

-- 1. countries
LOAD DATA INFILE '/var/lib/mysql-files/countries.csv'
INTO TABLE countries
FIELDS TERMINATED BY ',' OPTIONALLY ENCLOSED BY '"'
LINES TERMINATED BY '\n'
IGNORE 1 LINES
(country_id, country_name);

SELECT 'countries load done' AS status;


-- 2. interests
LOAD DATA INFILE '/var/lib/mysql-files/interests.csv'
INTO TABLE interests
FIELDS TERMINATED BY ',' OPTIONALLY ENCLOSED BY '"'
LINES TERMINATED BY '\n'
IGNORE 1 LINES
(interest_id, interest_name);

SELECT 'interests load done' AS status;


-- 3. advertisers
LOAD DATA INFILE '/var/lib/mysql-files/advertisers.csv'
INTO TABLE advertisers
FIELDS TERMINATED BY ',' OPTIONALLY ENCLOSED BY '"'
LINES TERMINATED BY '\n'
IGNORE 1 LINES
(advertiser_id, advertiser_name);

SELECT 'advertisers load done' AS status;


-- 4. users
LOAD DATA INFILE '/var/lib/mysql-files/users_fact.csv'
INTO TABLE users
FIELDS TERMINATED BY ',' OPTIONALLY ENCLOSED BY '"'
LINES TERMINATED BY '\n'
IGNORE 1 LINES
(user_id, age, gender, country_id, signup_date);

SELECT 'users load done' AS status;


-- 5. user_interests
LOAD DATA INFILE '/var/lib/mysql-files/user_interests.csv'
INTO TABLE user_interests
FIELDS TERMINATED BY ',' OPTIONALLY ENCLOSED BY '"'
LINES TERMINATED BY '\n'
IGNORE 1 LINES
(user_id, interest_id);

SELECT 'user_interests load done' AS status;


-- 6. campaigns
LOAD DATA INFILE '/var/lib/mysql-files/campaigns.csv'
INTO TABLE campaigns
FIELDS TERMINATED BY ',' OPTIONALLY ENCLOSED BY '"'
LINES TERMINATED BY '\n'
IGNORE 1 LINES
(
    campaign_id,
    advertiser_id,
    campaign_name,
    campaign_start_date,
    campaign_end_date,
    budget
);

SELECT 'campaigns load done' AS status;


-- 7. campaign_targeting
LOAD DATA INFILE '/var/lib/mysql-files/campaign_targeting.csv'
INTO TABLE campaign_targeting
FIELDS TERMINATED BY ',' OPTIONALLY ENCLOSED BY '"'
LINES TERMINATED BY '\n'
IGNORE 1 LINES
(
    campaign_id,
    age_min,
    age_max,
    target_interest_id,
    target_country_id
);

SELECT 'campaign_targeting load done' AS status;


-- 8. impressions
LOAD DATA INFILE '/var/lib/mysql-files/impressions.csv'
INTO TABLE impressions
FIELDS TERMINATED BY ',' OPTIONALLY ENCLOSED BY '"'
LINES TERMINATED BY '\n'
IGNORE 1 LINES
(
    impression_id,
    campaign_id,
    user_id,
    ad_slot_size,
    device,
    served_country_id,
    event_timestamp,
    bid_amount,
    ad_cost
);

SELECT 'impressions load done' AS status;


-- 9. clicks
LOAD DATA INFILE '/var/lib/mysql-files/clicks.csv'
INTO TABLE clicks
FIELDS TERMINATED BY ',' OPTIONALLY ENCLOSED BY '"'
LINES TERMINATED BY '\n'
IGNORE 1 LINES
(
    @click_id_raw,
    impression_id,
    @click_ts_str,
    ad_revenue
)
SET 
    click_id = REPLACE(@click_id_raw, '-click', ''),
    click_timestamp = NULLIF(@click_ts_str, '');

SELECT 'clicks load done' AS status;


SET FOREIGN_KEY_CHECKS = 1;
