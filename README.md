# AdTech Data Engineering — v2 (hw1_fixed)

> **This is an updated version of the original submission.**
> Original branch: [main](https://github.com/verestv/Data_Engineering/tree/main)
> Updated branch: [hw1_fixed](https://github.com/verestv/Data_Engineering/tree/hw1_fixed)

---

## What Changed and Why

This version addresses all feedback provided after the initial review.
Below is a summary of every change, the reason behind it, and where to find it in the repository.

### 1. `ad_events` split into `impressions` + `clicks`

**What changed:** The single `ad_events` table was replaced by two separate tables — `impressions` and `clicks`.

**Why:** Impressions and clicks are different types of events with different cardinality. Every ad served generates exactly one impression, but a click only exists when the user interacted with it. In practice, roughly 90% of rows have no click, which means storing them together forces NULL values in most rows. Separate tables allow independent indexing, cleaner aggregations (e.g. CTR), and a clearer data model.

- `impressions` — one row per ad served
- `clicks` — one row per user click, referencing its parent `impression_id`

```
impressions (impression_id, campaign_id, user_id, ad_slot_size,
             device, served_country_id, event_timestamp, bid_amount, ad_cost)

clicks      (click_id, impression_id, click_timestamp, ad_revenue)
```

---

### 2. `was_clicked` column removed

**What changed:** The `was_clicked` boolean column was removed entirely.

**Why:** It is a derived field — if a row exists in the `clicks` table for a given `impression_id`, the ad was clicked. Storing it separately risks inconsistency (e.g. `was_clicked = TRUE` but no corresponding `click_timestamp`). The click can always be inferred with a simple LEFT JOIN:

```sql
-- Check if an impression was clicked
SELECT i.impression_id,
       CASE WHEN c.click_id IS NOT NULL THEN 1 ELSE 0 END AS was_clicked
FROM impressions i
LEFT JOIN clicks c ON c.impression_id = i.impression_id;
```

---

### 3. `remaining_budget` removed from `campaigns`

**What changed:** The `remaining_budget` column was removed from the `campaigns` table.

**Why:** It is always derivable as `budget - SUM(impressions.ad_cost)`. Storing it means it must be updated every time a new impression is recorded — if that update is missed, the value becomes incorrect and misleads any query that uses it. Computed on demand it is always accurate:

```sql
SELECT
    c.campaign_id,
    c.campaign_name,
    c.budget,
    c.budget - COALESCE(SUM(i.ad_cost), 0) AS remaining_budget
FROM campaigns c
LEFT JOIN impressions i ON i.campaign_id = c.campaign_id
GROUP BY c.campaign_id, c.campaign_name, c.budget;
```

---

### 4. `targeting_criteria` replaced with `age_min` / `age_max`

**What changed:** The `targeting_criteria VARCHAR(255)` column (which stored values like `'25-45'`) in `campaign_targeting` was replaced with two integer columns: `age_min INT` and `age_max INT`.

**Why:** A free-text range string cannot be queried efficiently, cannot be validated with a CHECK constraint, and cannot be indexed meaningfully. Two integer columns allow:

```sql
-- Find users matching a campaign's age target
WHERE user.age BETWEEN ct.age_min AND ct.age_max
```

A CHECK constraint also enforces logical correctness at the database level:

```sql
CONSTRAINT chk_age_range CHECK (age_min > 0 AND age_max > age_min)
```

The `build_csvs.py` script parses the original string (`'25-45'`) into the two columns automatically using a regex.

---

### 5. Docker credentials moved to `.env` + healthcheck added

**What changed:** Hardcoded passwords were removed from `docker-compose.yml`. A `healthcheck` was added. MySQL version was pinned to `8.4` instead of `latest`.

**Why:** Credentials committed to a repository are a security risk. Docker Compose supports `env_file` to load variables from a local `.env` file that is excluded from version control. A healthcheck ensures the container reports as `healthy` only when MySQL is actually accepting connections, preventing race conditions when scripts try to connect immediately after startup.

| File | Purpose |
|------|---------|
| `.env` (not committed) | Actual credentials — copy from `.env_example` |
| `.env_example` | Template committed to the repo with placeholder values |
| `docker-compose.yml` | References `.env` via `env_file:`, includes `healthcheck` |

```bash
# Before starting, create your .env:
cp .env_example .env
# Then edit .env and set real passwords
```

---

### 6. `build_csvs.py` refactored into functions

**What changed:** The script was restructured from ~170 lines of top-level procedural code into focused functions with a `main()` entry point.

**Why:** Procedural scripts are hard to debug, test, and extend. Each function now has a single responsibility:

| Function | Responsibility |
|----------|---------------|
| `build_lookup()` | Generic dimension builder (reused for countries, interests, advertisers) |
| `build_countries()` | Extracts country dimension from `users.csv` |
| `build_interests()` | Extracts and explodes multi-value interest column |
| `build_users_fact()` | Builds user fact table with FK references |
| `build_user_interests()` | Builds bridge table |
| `extend_lookup()` | Appends new dimension values found in the ad events data |
| `build_advertisers()` | Extracts advertiser dimension |
| `build_campaigns()` | Builds campaign table, excludes `remaining_budget` |
| `build_campaign_targeting()` | Parses `targeting_criteria` → `age_min`/`age_max` |
| `build_impressions_and_clicks()` | Splits events into two separate output CSVs |
| `main()` | Orchestrates the full pipeline |

---

### 7. CHECK constraints added to all tables

**What changed:** `CHECK` constraints were added to enforce data integrity at the storage layer (supported in MySQL 8.0.16+).

**Why:** Invalid data — negative ages, inverted date ranges, zero budgets — is rejected before it reaches the tables, rather than silently corrupting aggregations later.

| Table | Constraint |
|-------|-----------|
| `users` | `age > 0 AND age < 150` |
| `campaigns` | `campaign_end_date > campaign_start_date`, `budget > 0` |
| `campaign_targeting` | `age_min > 0 AND age_max > age_min` |
| `impressions` | `bid_amount >= 0`, `ad_cost >= 0` |
| `clicks` | `ad_revenue >= 0` |

---

## Repository Structure

```
Data_Engineering/  (branch: hw1_fixed)
│
├── init/
│   └── ddl_scripts.sql        # CREATE TABLE statements — auto-run by Docker on first start
│
├── build_csvs.py              # ETL: transforms source CSVs into one CSV per table
├── change_csv_headers.py      # Renames CamelCase headers to snake_case
├── read_csv.py                # Utility: preview first 15 rows of any CSV
├── load_all.sql               # LOAD DATA INFILE commands for all 9 tables
│
├── .env_example               # Credential template (copy to .env, never commit .env)
├── docker-compose.yml         # MySQL 8.4 with env_file + healthcheck
├── .gitignore                 # Excludes *.csv, venv/, .env
├── new_db_schema.png          # Visual ER diagram of the updated schema
└── README.md                  # This file
```

---

## Schema Overview

```
countries ──────────── users ──── user_interests ──── interests
                         │
advertisers ─── campaigns ─── campaign_targeting
                     │            (age_min, age_max,
                impressions        target_interest_id,
                     │             target_country_id)
                   clicks
```

**Tables:** `advertisers`, `countries`, `interests`, `users`, `user_interests`, `campaigns`, `campaign_targeting`, `impressions`, `clicks`

Full DDL with inline comments explaining each decision: [`init/ddl_scripts.sql`](init/ddl_scripts.sql)

---

## Quick Start

### 1. Clone and set up environment

```bash
git clone https://github.com/verestv/Data_Engineering.git
cd Data_Engineering
git checkout hw1_fixed

cp .env_example .env
# Edit .env — set MYSQL_ROOT_PASSWORD and MYSQL_PASSWORD
```

### 2. Start MySQL

```bash
docker compose up -d

# Wait until healthy
docker inspect --format='{{.State.Health.Status}}' adtech_mysql
# → healthy
```

> Docker automatically runs `init/ddl_scripts.sql` on the first start, creating all tables.

### 3. Rename CSV headers

```bash
python3 change_csv_headers.py
# Reads ad_events.csv, writes ad_events_header_updated.csv
# Original file is NOT modified
```

### 4. Build dimension and fact CSVs

```bash
python3 build_csvs.py
```

Expected output:
```
=== Reading source files ===
=== Building dimensions from users.csv ===
countries.csv          —        5 rows
interests.csv          —        8 rows
users_fact.csv         —  700,000 rows
user_interests.csv     — 1,748,972 rows
=== Extending dimensions with adtech data ===
=== Building adtech tables ===
advertisers.csv        —      100 rows
campaigns.csv          —    1,013 rows
campaign_targeting.csv —    1,013 rows
impressions.csv        — 10,000,000 rows
clicks.csv             —  ~1,000,000 rows
=== All CSVs generated. Ready for LOAD DATA INFILE. ===
```

### 5. Copy CSVs into the container and load data

```bash
# Copy all generated CSVs into the container
for f in countries interests advertisers users_fact user_interests \
          campaigns campaign_targeting impressions clicks; do
    docker cp ${f}.csv adtech_mysql:/var/lib/mysql-files/${f}.csv
done

# Copy and run the load script
docker cp load_all.sql adtech_mysql:/tmp/load_all.sql
docker exec -it adtech_mysql mysql -uroot -p adtech_db < /tmp/load_all.sql
```

Each table prints a status line as it loads. The script prints `X load done` after each table so you can track progress.

### 6. Verify data

```bash
docker exec -it adtech_mysql mysql -uroot -p adtech_db
```

```sql
SELECT * FROM advertisers        LIMIT 10;
SELECT * FROM countries          LIMIT 10;
SELECT * FROM interests          LIMIT 10;
SELECT * FROM users              LIMIT 10;
SELECT * FROM user_interests     LIMIT 10;
SELECT * FROM campaigns          LIMIT 10;
SELECT * FROM campaign_targeting LIMIT 10;
SELECT * FROM impressions        LIMIT 10;
SELECT * FROM clicks             LIMIT 10;
```

---

## Key Queries

### Click-Through Rate (CTR) per campaign

```sql
SELECT
    c.campaign_name,
    COUNT(i.impression_id)                                       AS impressions,
    COUNT(cl.click_id)                                           AS clicks,
    ROUND(COUNT(cl.click_id) * 100.0 / COUNT(i.impression_id), 4) AS ctr_pct
FROM campaigns c
LEFT JOIN impressions i  ON i.campaign_id    = c.campaign_id
LEFT JOIN clicks cl      ON cl.impression_id = i.impression_id
GROUP BY c.campaign_id, c.campaign_name
ORDER BY ctr_pct DESC;
```

### Remaining budget per campaign (derived, not stored)

```sql
SELECT
    c.campaign_name,
    c.budget,
    COALESCE(SUM(i.ad_cost), 0)             AS spent,
    c.budget - COALESCE(SUM(i.ad_cost), 0)  AS remaining_budget
FROM campaigns c
LEFT JOIN impressions i ON i.campaign_id = c.campaign_id
GROUP BY c.campaign_id, c.campaign_name, c.budget;
```

### Total advertiser spending

```sql
SELECT
    a.advertiser_name,
    SUM(i.ad_cost)     AS total_spend,
    SUM(cl.ad_revenue) AS total_revenue
FROM advertisers a
JOIN campaigns   c  ON c.advertiser_id   = a.advertiser_id
JOIN impressions i  ON i.campaign_id     = c.campaign_id
LEFT JOIN clicks cl ON cl.impression_id  = i.impression_id
GROUP BY a.advertiser_id, a.advertiser_name
ORDER BY total_spend DESC;
```
