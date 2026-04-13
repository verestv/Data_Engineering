# Homework 5 – REST API with Redis Caching

This homework builds a FastAPI REST API that serves advertising analytics queries backed by MySQL. Redis is used as a read-through cache in front of the database to reduce latency and DB load.

The MySQL container reuses the existing data volume from Homework 1 (hw1_fixed) repo

---

## Folder Structure

- `docker-compose.yml`  
  Spins up three containers: `adtech_mysql_hw5` (existing volume), `redis_hw5`, `api_hw5`

- `app/main.py`  
  FastAPI application with 3 endpoints and read-through Redis cache logic

- `app/database.py`  
  MySQL connection pool (5 connections via `mysql-connector-python`)

- `app/cache.py`  
  Redis helpers: `cache_get`, `cache_set`, `cache_delete`

- `app/Dockerfile`  
  Builds the API image from `python:3.12-slim`

- `app/requirements.txt`  
  Python dependencies

- `benchmark/benchmark.py`  
  Measures MISS vs HIT response times across all 3 endpoints and prints a summary table
  Details with benchmark results are in `benchmark` folder

---

## Endpoints

| Method | Path | Description | Cache TTL |
|--------|------|-------------|-----------|
| GET | `/campaign/{id}/performance` | CTR, impressions, clicks, ad spend | 30 seconds |
| GET | `/advertiser/{id}/spending` | Total spend, revenue, campaigns | 5 minutes |
| GET | `/user/{id}/engagements` | Last 20 ads seen + click info | 60 seconds |
| GET | `/health` | Health check | none |

Each response includes a `"cache": "HIT"` or `"cache": "MISS"` field.

---

## Step 1 — Start All Containers

```bash
docker compose up -d --build
```

---

## Step 2 — Test Endpoints

```bash
# Campaign performance
curl http://localhost:8000/campaign/159/performance
output: {"campaign_id":159,"campaign_name":"Campaign_137","advertiser_name":"Advertiser_14","total_impressions":9832,"total_clicks":485,"ctr_percent":4.932

# Advertiser spending
curl http://localhost:8000/advertiser/2/spending
output:
{"advertiser_id":2,"advertiser_name":"Advertiser_10","total_campaigns":11,"total_impressions":108200,"total_clicks":5239,"total_ad_spend":245452.87,"total_ad_revenue":27568.55,"cache":"MISS"}

# User engagements
curl http://localhost:8000/user/583398/engagements
```

Or open the interactive docs:

```
http://localhost:8000/docs (screenshot: fastapi_gui.png)
```

First call returns `"cache": "MISS"` — data fetched from MySQL.  
Second call returns `"cache": "HIT"` — data served from Redis instantly.

---

## Step 3 — Run Benchmark

Install requests if not already installed:

```bash
pip install requests
```

Run the benchmark (15 requests per endpoint by default):

```bash
cd benchmark/
python benchmark.py --host http://localhost:8000 --runs 15
```
results in `benchmark/bm_results.txt


