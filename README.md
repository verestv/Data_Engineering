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

**Important:** Set the date window at the top of the session first:

```sql
SET @start_date = '2024-11-01'; 
SET @end_date   = '2024-11-30';
```

### 2. Run queries.sql

```bash
docker cp queries.sql adtech_mysql:/tmp/queries.sql
docker exec -it adtech_mysql mysql -uroot -p adtech_db < /tmp/queries.sql
```

Or open the file and run queries individually.

---

## Query results

> query results are in sql_results_from_queries.txt

---

## Python report script — report.py

The script connects to MySQL, runs all 7 queries, and exports results.

### Install dependencies

```bash
activate venv, then:
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

