# AdTech SQL Analytics — Homework 2

> **Updated schema from:** [hw1_fixed](https://github.com/verestv/Data_Engineering/tree/hw1_fixed)
> **This branch:** [hw2](https://github.com/verestv/Data_Engineering/tree/hw2)

---

## Overview

This homework performs SQL analytics on the AdTech database introduced in HW1.
We use the **updated schema from the `hw1_fixed` branch**, which normalizes
the original `ad_events` table into separate `impressions` and `clicks` tables.

All 7 business questions are answered with SQL queries, supported by a Python
script that automates execution and exports results.

---

## Schema

The schema is defined and documented in the
[hw1_fixed branch](https://github.com/verestv/Data_Engineering/tree/hw1_fixed).
We connect to the **same MySQL Docker container** set up in HW1

---

## Connect to MySQL (same Docker container as HW1)

```bash

# Connect interactively
docker exec -it adtech_mysql mysql -uroot -p adtech_db
```
---

## Files

| File | Description |
|------|-------------|
| `indexes.sql` | 6 indexes to create before running any queries |
| `queries.sql` | All 7 SQL queries with detailed comments |
| `report.py` | Python script — runs all queries, exports CSV + JSON |
| `reports/` | Output folder: one CSV per query + combined JSON |
| `docker-compose.yml` | MySQL 8.4 (reused from hw1_fixed, no changes) |
| `.env_example` | Credential template |

---

## Step-by-step: Run the SQL queries

### 1. Create indexes

Run this once before any queries. Without indexes, MySQL will full-scan
the 10M+ impressions table on every query.

```bash
docker cp indexes.sql adtech_mysql:/tmp/indexes.sql
docker exec -it adtech_mysql mysql -uroot -p adtech_db < /tmp/indexes.sql
```

Or inside the MySQL shell:

```sql
SOURCE /tmp/indexes.sql;
```

### 2. Run queries.sql

```bash
docker cp queries.sql adtech_mysql:/tmp/queries.sql
docker exec -it adtech_mysql mysql -uroot -p adtech_db < /tmp/queries.sql
```

Or open the file in MySQL Workbench / DBeaver and run queries individually.

**Important:** Set the date window at the top of the session first:

```sql
SET @start_date = '2024-01-01';
SET @end_date   = '2024-01-31';
```

---

## SQL Queries

### Q1 — Top 5 campaigns by CTR
Finds which campaigns are most effective at getting users to click.
CTR = clicks / impressions × 100.

### Q2 — Top advertiser spenders with ROAS
Shows which advertisers spend the most and whether they get a return.
ROAS = revenue / spend. ROAS > 1 means profitable.

### Q3 — CPC and CPM per campaign
Efficiency metrics per campaign.
CPC = spend / clicks. CPM = spend / impressions × 1000.

### Q4 — Top countries by ad revenue
Revenue grouped by the country where the impression was served.

### Q5 — Top 10 most engaged users
Users with the most clicks, with their age, gender, and country.

### Q6 — Campaigns above 80% budget consumed
Budget consumption is a lifetime metric (not windowed).
Remaining budget = `budget - SUM(impressions.ad_cost)`.

### Q7 — CTR by device type
Compares CTR, avg CPC, and impression share across device types (mobile, desktop, tablet).
Uses a window function to compute each device's share of total impressions.

---

## Metric formulas

| Metric | Formula |
|--------|---------|
| CTR | `COUNT(clicks) / COUNT(impressions) × 100` |
| CPC | `SUM(ad_cost) / COUNT(clicks)` |
| CPM | `SUM(ad_cost) / COUNT(impressions) × 1000` |
| ROAS | `SUM(ad_revenue) / SUM(ad_cost)` |
| Remaining budget | `budget - SUM(impressions.ad_cost)` |

---

## Screenshots of query results

> _Screenshots will be added here after running the queries._

| Query | Screenshot |
|-------|------------|
| Q1 — Top 5 campaigns by CTR | _(coming soon)_ |
| Q2 — Top advertiser spenders | _(coming soon)_ |
| Q3 — CPC and CPM | _(coming soon)_ |
| Q4 — Top countries by revenue | _(coming soon)_ |
| Q5 — Top 10 users | _(coming soon)_ |
| Q6 — Budget consumption | _(coming soon)_ |
| Q7 — CTR by device | _(coming soon)_ |

---

## Python report script — report.py

The script connects to MySQL, runs all 7 queries, and exports results.

### Install dependencies

```bash
pip install mysql-connector-python pandas
```

### Run

```bash
# Simplest — pass the password inline
DB_PASSWORD=your_root_pass python3 report.py

# Or export all variables first
export DB_HOST=127.0.0.1
export DB_PORT=3306
export DB_USER=root
export DB_PASSWORD=your_root_pass
export DB_NAME=adtech_db
python3 report.py
```

### Output

The script prints each query result to the terminal and saves files to `reports/`:

```
============================================================
  Q1 — Top 5 Campaigns by CTR
============================================================
 campaign_name  advertiser_name  impressions  clicks  ctr_pct
 ...
  -> 5 rows saved to reports/q1_top_ctr_campaigns.csv

...

Full JSON report -> reports/report_20240101_120000.json
Done.
```

### Output files

| File | Contents |
|------|----------|
| `reports/q1_top_ctr_campaigns.csv` | Q1 result |
| `reports/q2_advertiser_spend.csv` | Q2 result |
| `reports/q3_cpc_cpm.csv` | Q3 result |
| `reports/q4_revenue_by_country.csv` | Q4 result |
| `reports/q5_top_users.csv` | Q5 result |
| `reports/q6_budget_consumption.csv` | Q6 result |
| `reports/q7_device_ctr.csv` | Q7 result |
| `reports/report_TIMESTAMP.json` | All results combined |

---

## Index strategy

All indexes are on the `impressions` table (the largest table):

| Index | Columns | Used in |
|-------|---------|---------|
| `idx_imp_timestamp` | `event_timestamp` | All queries |
| `idx_imp_campaign_ts` | `campaign_id, event_timestamp` | Q1, Q2, Q3, Q6 |
| `idx_imp_device_ts` | `device, event_timestamp` | Q7 |
| `idx_imp_country_ts` | `served_country_id, event_timestamp` | Q4 |
| `idx_imp_user` | `user_id` | Q5 |
| `idx_clicks_imp_id` | `clicks(impression_id)` | All (JOIN) |
