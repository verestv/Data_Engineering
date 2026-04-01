-- ============================================================
-- AdTech Database Schema — v2 (teacher feedback aligned)
-- ============================================================

-- 1. advertisers
-- Stores each advertiser once with a surrogate PK.
-- UNIQUE on name prevents duplicates, keeps campaign references stable.
CREATE TABLE advertisers (
    advertiser_id BIGINT NOT NULL AUTO_INCREMENT,
    advertiser_name VARCHAR(255) NOT NULL,
    PRIMARY KEY (advertiser_id),
    UNIQUE KEY uq_advertiser_name (advertiser_name)
);

-- 2. countries
-- Dimension table: normalises country names, avoids string repetition in facts.
CREATE TABLE countries (
    country_id INT NOT NULL AUTO_INCREMENT,
    country_name VARCHAR(100) NOT NULL,
    PRIMARY KEY (country_id),
    UNIQUE KEY uq_country_name (country_name)
);

-- 3. interests
-- Central lookup for all user and campaign interests.
-- INT key reduces storage compared to repeating strings.
CREATE TABLE interests (
    interest_id INT NOT NULL AUTO_INCREMENT,
    interest_name VARCHAR(100) NOT NULL,
    PRIMARY KEY (interest_id),
    UNIQUE KEY uq_interest_name (interest_name)
);

-- 4. users
-- User profiles. FK to countries enforces valid country.
-- CHECK ensures age is a realistic positive value.
CREATE TABLE users (
    user_id BIGINT NOT NULL,
    age INT NOT NULL,
    gender VARCHAR(50) NOT NULL,
    country_id INT NOT NULL,
    signup_date DATE NOT NULL,
    PRIMARY KEY (user_id),
    CONSTRAINT chk_user_age CHECK (age > 0 AND age < 150),
    CONSTRAINT fk_users_country
        FOREIGN KEY (country_id) REFERENCES countries(country_id)
);

-- 5. user_interests
-- Bridge table: many-to-many between users and interests.
-- Composite PK prevents duplicate user-interest pairs.
CREATE TABLE user_interests (
    user_id BIGINT NOT NULL,
    interest_id INT NOT NULL,
    PRIMARY KEY (user_id, interest_id),
    CONSTRAINT fk_ui_user
        FOREIGN KEY (user_id) REFERENCES users(user_id),
    CONSTRAINT fk_ui_interest
        FOREIGN KEY (interest_id) REFERENCES interests(interest_id)
);

-- 6. campaigns
-- One row per campaign, linked to its advertiser.
-- remaining_budget is REMOVED — it is derived (budget - SUM(impressions.ad_cost)).
-- CHECK constraints prevent inverted dates and zero/negative budgets.
CREATE TABLE campaigns (
    campaign_id BIGINT NOT NULL AUTO_INCREMENT,
    advertiser_id BIGINT NOT NULL,
    campaign_name VARCHAR(255) NOT NULL,
    campaign_start_date DATE NOT NULL,
    campaign_end_date DATE NOT NULL,
    budget DECIMAL(14,2) NOT NULL,
    PRIMARY KEY (campaign_id),
    CONSTRAINT chk_campaign_dates
        CHECK (campaign_end_date > campaign_start_date),
    CONSTRAINT chk_campaign_budget
        CHECK (budget > 0),
    UNIQUE KEY uq_campaign (
        advertiser_id,
        campaign_name,
        campaign_start_date,
        campaign_end_date
    ),
    CONSTRAINT fk_campaigns_advertiser
        FOREIGN KEY (advertiser_id) REFERENCES advertisers(advertiser_id)
);

-- 7. campaign_targeting
-- Targeting config separated from campaigns (single responsibility).
-- targeting_criteria VARCHAR is REPLACED by age_min/age_max INT columns
-- so that queries like WHERE age BETWEEN age_min AND age_max work natively.
-- CHECK ensures age range is logical (positive, max > min).
CREATE TABLE campaign_targeting (
    campaign_id BIGINT NOT NULL,
    age_min INT NOT NULL,
    age_max INT NOT NULL,
    target_interest_id INT NOT NULL,
    target_country_id INT NOT NULL,
    PRIMARY KEY (campaign_id),
    CONSTRAINT chk_age_range
        CHECK (age_min > 0 AND age_max > age_min),
    CONSTRAINT fk_ct_campaign
        FOREIGN KEY (campaign_id) REFERENCES campaigns(campaign_id),
    CONSTRAINT fk_ct_interest
        FOREIGN KEY (target_interest_id) REFERENCES interests(interest_id),
    CONSTRAINT fk_ct_country
        FOREIGN KEY (target_country_id) REFERENCES countries(country_id)
);

-- 8. impressions
-- One row per ad served (impression event).
-- was_clicked is REMOVED — presence of a row in clicks table means it was clicked.
-- Separated from clicks because impressions always exist, clicks do not.
-- CHECK prevents negative monetary values.
CREATE TABLE impressions (
    impression_id CHAR(36) NOT NULL,
    campaign_id BIGINT NOT NULL,
    user_id BIGINT NOT NULL,
    ad_slot_size VARCHAR(50) NOT NULL,
    device VARCHAR(50) NOT NULL,
    served_country_id INT NOT NULL,
    event_timestamp DATETIME NOT NULL,
    bid_amount DECIMAL(10,2) NOT NULL,
    ad_cost DECIMAL(10,2) NOT NULL,
    PRIMARY KEY (impression_id),
    CONSTRAINT chk_bid CHECK (bid_amount >= 0),
    CONSTRAINT chk_cost CHECK (ad_cost >= 0),
    CONSTRAINT fk_imp_campaign
        FOREIGN KEY (campaign_id) REFERENCES campaigns(campaign_id),
    CONSTRAINT fk_imp_user
        FOREIGN KEY (user_id) REFERENCES users(user_id),
    CONSTRAINT fk_imp_country
        FOREIGN KEY (served_country_id) REFERENCES countries(country_id)
);

-- 9. clicks
-- One row per user click, referencing its parent impression.
-- A click without an impression cannot exist (FK enforces this).
-- ad_revenue lives here because revenue only occurs when a click happens.
CREATE TABLE clicks (
    click_id CHAR(36) NOT NULL,
    impression_id CHAR(36) NOT NULL,
    click_timestamp DATETIME NOT NULL,
    ad_revenue DECIMAL(10,2) NOT NULL DEFAULT 0.00,
    PRIMARY KEY (click_id),
    CONSTRAINT chk_revenue CHECK (ad_revenue >= 0),
    CONSTRAINT fk_click_impression
        FOREIGN KEY (impression_id) REFERENCES impressions(impression_id)
);
