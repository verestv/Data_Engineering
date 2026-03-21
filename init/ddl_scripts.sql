CREATE TABLE advertisers (
    advertiser_id BIGINT NOT NULL AUTO_INCREMENT,
    advertiser_name VARCHAR(255) NOT NULL,
    PRIMARY KEY (advertiser_id),
    UNIQUE KEY uq_advertiser_name (advertiser_name)
);
-- Stores each advertiser once with a surrogate primary key for joins.
-- The unique constraint on advertiser_name prevents duplicate advertisers
-- and keeps campaign references stable even if names are reused.

CREATE TABLE countries (
    country_id INT NOT NULL AUTO_INCREMENT,
    country_name VARCHAR(100) NOT NULL,
    PRIMARY KEY (country_id),
    UNIQUE KEY uq_country_name (country_name)
);
-- Normalizes country names into a separate dimension to avoid repetition.
-- The surrogate country_id is used in all fact tables to keep joins compact
-- and to ensure consistent country naming via the unique constraint.

CREATE TABLE interests (
    interest_id INT NOT NULL AUTO_INCREMENT,
    interest_name VARCHAR(100) NOT NULL,
    PRIMARY KEY (interest_id),
    UNIQUE KEY uq_interest_name (interest_name)
);
-- Central lookup for all possible user and campaign interests.
-- Using an integer interest_id reduces storage and enforces a single
-- canonical row per logical interest via the unique constraint.

CREATE TABLE users (
    user_id BIGINT NOT NULL,
    age INT NOT NULL,
    gender VARCHAR(50) NOT NULL,
    country_id INT NOT NULL,
    signup_date DATE NOT NULL,
    PRIMARY KEY (user_id),
    CONSTRAINT fk_users_country
        FOREIGN KEY (country_id) REFERENCES countries(country_id)
);
-- User profiles with a natural user_id preserved from the source.
-- The country_id foreign key enforces that every user belongs to a valid
-- country and avoids denormalized country strings on the user table.

CREATE TABLE user_interests (
    user_id BIGINT NOT NULL,
    interest_id INT NOT NULL,
    PRIMARY KEY (user_id, interest_id),
    CONSTRAINT fk_user_interests_user
        FOREIGN KEY (user_id) REFERENCES users(user_id),
    CONSTRAINT fk_user_interests_interest
        FOREIGN KEY (interest_id) REFERENCES interests(interest_id)
);
-- Bridge table modeling the many‑to‑many relationship between users
-- and interests without repeating interest names on the users table.
-- The composite primary key prevents duplicate user–interest pairs.

CREATE TABLE campaigns (
    campaign_id BIGINT NOT NULL AUTO_INCREMENT,
    advertiser_id BIGINT NOT NULL,
    campaign_name VARCHAR(255) NOT NULL,
    campaign_start_date DATE NOT NULL,
    campaign_end_date DATE NOT NULL,
    budget DECIMAL(14,2) NOT NULL,
    remaining_budget DECIMAL(14,2) NOT NULL,
    PRIMARY KEY (campaign_id),
    UNIQUE KEY uq_campaign_advertiser_name_dates (
        advertiser_id,
        campaign_name,
        campaign_start_date,
        campaign_end_date
    ),
    CONSTRAINT fk_campaigns_advertiser
        FOREIGN KEY (advertiser_id) REFERENCES advertisers(advertiser_id)
);
-- Stores each campaign with a surrogate campaign_id and links it to
-- its advertiser via advertiser_id for consistent joins.
-- The unique key on advertiser + name + date range prevents accidental
-- duplicate campaigns that would fragment spend and event data.

CREATE TABLE campaign_targeting (
    campaign_id BIGINT NOT NULL,
    targeting_criteria VARCHAR(255) NOT NULL,
    target_interest_id INT NOT NULL,
    target_country_id INT NOT NULL,
    PRIMARY KEY (campaign_id),
    CONSTRAINT fk_campaign_targeting_campaign
        FOREIGN KEY (campaign_id) REFERENCES campaigns(campaign_id),
    CONSTRAINT fk_campaign_targeting_interest
        FOREIGN KEY (target_interest_id) REFERENCES interests(interest_id),
    CONSTRAINT fk_campaign_targeting_country
        FOREIGN KEY (target_country_id) REFERENCES countries(country_id)
);
-- Captures targeting configuration as a separate table so campaigns
-- remain focused on commercial attributes (budget, dates, name).
-- Foreign keys to interests and countries ensure all targeting values
-- are valid lookups and consistent with other parts of the model.

CREATE TABLE ad_events (
    event_id CHAR(36) NOT NULL,
    campaign_id BIGINT NOT NULL,
    user_id BIGINT NOT NULL,
    ad_slot_size VARCHAR(50) NOT NULL,
    device VARCHAR(50) NOT NULL,
    served_country_id INT NOT NULL,
    event_timestamp DATETIME NOT NULL,
    bid_amount DECIMAL(10,2) NOT NULL,
    ad_cost DECIMAL(10,2) NOT NULL,
    was_clicked BOOLEAN NOT NULL,
    click_timestamp DATETIME NULL,
    ad_revenue DECIMAL(10,2) NOT NULL DEFAULT 0.00,
    PRIMARY KEY (event_id),
    CONSTRAINT fk_ad_events_campaign
        FOREIGN KEY (campaign_id) REFERENCES campaigns(campaign_id),
    CONSTRAINT fk_ad_events_user
        FOREIGN KEY (user_id) REFERENCES users(user_id),
    CONSTRAINT fk_ad_events_country
        FOREIGN KEY (served_country_id) REFERENCES countries(country_id)
);
-- Fact table at the ad impression/click event grain, keyed by a UUID
-- so events are globally unique and traceable across systems.
-- Foreign keys to campaigns, users, and countries enforce referential
-- integrity and make analytical joins reliable on all business dimensions.
