# AdTech Database — Homework 1

Normalized relational MySQL database built from two raw datasets:
- `users.csv` — user profile data
- `ad_events_header_updated.csv` — ad impression and click events

---

## Project Files

| `clean.py` | Cleans raw CSVs and splits them into normalized files |
| `02_load.py` | Loads clean CSVs into MySQL |
| `03_preview.py` | Shows first 10 rows of each table to verify data loaded correctly |

---

## Database Schema

7 tables in 3rd Normal Form (3NF). Each table represents one real-world entity.

```
advertisers  ──< campaigns
campaigns    ──< impressions
ad_slots     ──< impressions
users        ──< impressions
users        ──< user_interests
impressions  ──| clicks
```

`──<` one to many  
`──|` one to one

---

## DDL — Table Descriptions

### advertisers
`AdvertiserName` repeated on every single row in the raw CSV.
Instead of storing the string `'Advertiser_30'` millions of times, we store it once here and every campaign references it by `advertiser_id`.

```sql
CREATE TABLE advertisers (
    advertiser_id   INT             NOT NULL,
    name            VARCHAR(255)    NOT NULL UNIQUE,
    PRIMARY KEY (advertiser_id)
);
```

---

### ad_slots
`AdSlotSize` had only 3 unique values (`300x250`, `728x90`, `160x600`) but repeated on every impression row.
Extracted into its own table so we store each size string exactly once.

```sql
CREATE TABLE ad_slots (
    ad_slot_id  INT         NOT NULL,
    size        VARCHAR(20) NOT NULL,
    PRIMARY KEY (ad_slot_id)
);
```

---

### users
Comes directly from `users.csv`. One row per user.
`user_id` is the natural primary key from the source file. `BIGINT` used because IDs are large numbers like `656312`.

```sql
CREATE TABLE users (
    user_id     BIGINT      NOT NULL,
    age         INT,
    gender      VARCHAR(20),
    location    VARCHAR(100),
    signup_date DATE,
    PRIMARY KEY (user_id)
);
```

---

### user_interests
In `users.csv` the `Interests` column stored multiple values in one cell — `'Gaming,Sports,Health'`.
This violates 1NF (one value per cell). Split into one row per interest per user so interests can be properly queried and joined.

```sql
CREATE TABLE user_interests (
    id          INT          NOT NULL AUTO_INCREMENT,
    user_id     BIGINT       NOT NULL,
    interest    VARCHAR(100) NOT NULL,
    PRIMARY KEY (id),
    FOREIGN KEY (user_id) REFERENCES users(user_id)
);
```

---

### campaigns
In the raw CSV, campaign columns (`CampaignName`, `CampaignStartDate`, `CampaignEndDate`, targeting columns, `Budget`, `RemainingBudget`) repeated on every single event row.
All of this describes the campaign — not the individual ad event. Stored here once, linked via `campaign_id`.

```sql
CREATE TABLE campaigns (
    campaign_id                     INT             NOT NULL,
    advertiser_id                   INT             NOT NULL,
    campaign_name                   VARCHAR(255)    NOT NULL,
    campaign_start_date             DATE            NOT NULL,
    campaign_end_date               DATE            NOT NULL,
    campaign_targeting_criteria     VARCHAR(100),
    campaign_targeting_interest     VARCHAR(100),
    campaign_targeting_country      VARCHAR(100),
    budget                          DECIMAL(12,2)   NOT NULL,
    remaining_budget                DECIMAL(12,2)   NOT NULL,
    PRIMARY KEY (campaign_id),
    FOREIGN KEY (advertiser_id) REFERENCES advertisers(advertiser_id)
);
```

---

### impressions
Core fact table — one row per ad serving event (`EventID` from the raw CSV).
`device` and `location` live here because the same campaign can serve ads across different devices and geographies.
`bid_amount` and `ad_cost` are per-auction values that belong to the event, not the campaign.
`impression_timestamp` renamed from `Timestamp` to avoid conflict with MySQL reserved word.

```sql
CREATE TABLE impressions (
    event_id                CHAR(36)        NOT NULL,
    campaign_id             INT             NOT NULL,
    ad_slot_id              INT             NOT NULL,
    user_id                 BIGINT          NOT NULL,
    device                  VARCHAR(20)     NOT NULL,
    location                VARCHAR(100)    NOT NULL,
    impression_timestamp    DATETIME        NOT NULL,
    bid_amount              DECIMAL(10,2)   NOT NULL,
    ad_cost                 DECIMAL(10,2)   NOT NULL,
    PRIMARY KEY (event_id),
    FOREIGN KEY (campaign_id)  REFERENCES campaigns(campaign_id),
    FOREIGN KEY (ad_slot_id)   REFERENCES ad_slots(ad_slot_id),
    FOREIGN KEY (user_id)      REFERENCES users(user_id)
);
```

---

### clicks
In the raw CSV, `WasClicked`, `ClickTimestamp`, and `AdRevenue` were present on every row but empty or zero when the ad was not clicked — the majority of rows.
Storing clicks as a separate child table eliminates wasted space. If a row exists here, the impression was clicked. If not, it was not.
CTR then becomes simply `COUNT(clicks) / COUNT(impressions)`.
`UNIQUE` on `event_id` enforces one click per impression.
`WasClicked` column from the CSV is not stored — it is implicit from the existence of a row.

```sql
CREATE TABLE clicks (
    click_id            CHAR(36)        NOT NULL,
    event_id            CHAR(36)        NOT NULL UNIQUE,
    click_timestamp     DATETIME        NOT NULL,
    ad_revenue          DECIMAL(10,2)   NOT NULL,
    PRIMARY KEY (click_id),
    FOREIGN KEY (event_id) REFERENCES impressions(event_id)
);
```

---

## clean.py — What It Does

Reads both raw CSV files and produces 7 clean CSV files ready for database loading.

**Users cleaning:**
- Reads `users.csv` row by row
- Splits the `Interests` comma-separated list into individual rows → `clean_user_interests.csv`
- Saves clean user rows → `clean_users.csv`

**Ad events cleaning:**
- Reads `ad_events_header_updated.csv` row by row (file is ~10M rows, never loaded fully into memory)
- Strips leading whitespace from `CampaignTargetingInterest` and `CampaignTargetingCountry`
- Extracts unique advertisers → `clean_advertisers.csv`
- Extracts unique campaigns → `clean_campaigns.csv`
- Extracts unique ad slot sizes → `clean_ad_slots.csv`
- Writes one impression row per event → `clean_impressions.csv`
- Writes one click row only for events where `WasClicked = True` → `clean_clicks.csv`

**Output files:**

| File | Contents |
|---|---|
| `clean_advertisers.csv` | Unique advertisers with IDs |
| `clean_ad_slots.csv` | Unique slot sizes with IDs |
| `clean_users.csv` | One row per user |
| `clean_user_interests.csv` | One row per interest per user |
| `clean_campaigns.csv` | One row per campaign |
| `clean_impressions.csv` | One row per ad serving event |
| `clean_clicks.csv` | One row per click event only |

---

## 02_load.py — What It Does

Loads all 7 clean CSV files into MySQL using `LOAD DATA LOCAL INFILE` — reads CSV files directly from disk into the database without row-by-row Python loops.

Three settings that speed up the bulk load:
- `SET FOREIGN_KEY_CHECKS = 0` — skips FK validation during load, re-enabled after
- `SET UNIQUE_CHECKS = 0` — skips unique validation during load, re-enabled after
- `SET AUTOCOMMIT = 0` — one single commit at the end instead of one per row

Timestamps in the CSV use `T` as separator (`2024-10-31T06:56:39`).
Before loading, these are fixed with `sed` so MySQL reads them directly without conversion:

```bash
sed 's/T/ /' clean_impressions.csv > clean_impressions_fixed.csv
sed 's/T/ /' clean_clicks.csv > clean_clicks_fixed.csv
```

---

## MySQL Server

Running locally via Docker or direct MySQL installation.

```bash
# Connect with local infile enabled
mysql --local-infile=1 -u ivan -p

# Enable local infile on server side (run once)
SET GLOBAL local_infile = 1;
```

---

## Setup — Run Order

```bash
# 1. Create tables
mysql --local-infile=1 -u ivan -p < 01_create_tables.sql

# 2. Clean raw data
python3 clean.py

# 3. Fix timestamps in large files
sed 's/T/ /' clean_impressions.csv > clean_impressions_fixed.csv
sed 's/T/ /' clean_clicks.csv > clean_clicks_fixed.csv

# 4. Load into database
python3 02_load.py

# 5. Verification of data in db
db_data.md
```

---

## 03_preview.py — What It Does

Connects to MySQL and prints the first 10 rows of each table with row counts.
Used to verify that all data loaded correctly after running `02_load.py`.
