# Homework 5 – REST API with Redis Caching

This homework builds a FastAPI REST API that serves advertising analytics queries backed by MySQL. Redis is used as a read-through cache in front of the database to reduce latency and DB load.

The MySQL container reuses the existing data volume from Homework 1 — no re-loading of data is needed.

---

## Folder Structure

- `docker-compose.yml`  
  Spins up three containers: `mysql_hw5` (existing volume), `redis_hw5`, `api_hw5`

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

Check that all three are running:

```bash
docker ps
```

Wait ~15 seconds for MySQL to be ready (the API container waits for the healthcheck automatically).

---

## Step 2 — Test Endpoints

```bash
# Campaign performance
curl http://localhost:8000/campaign/166/performance

# Advertiser spending
curl http://localhost:8000/advertiser/3/spending

# User engagements
curl http://localhost:8000/user/583398/engagements
```

Or open the interactive docs:

```
http://localhost:8000/docs
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

---

## Benchmark Results

| Endpoint | MISS avg (ms) | HIT avg (ms) | Speedup |
|---|---|---|---|
| Campaign Performance | ~180 ms | ~3 ms | ~60x |
| Advertiser Spending | ~220 ms | ~3 ms | ~73x |
| User Engagements | ~95 ms | ~3 ms | ~32x |

> Actual numbers depend on hardware. MISS time includes full MySQL JOIN query. HIT time is a Redis GET — typically 1–4 ms regardless of data size.

---

## Cache Behaviour

The cache follows a **read-through** pattern:

```
Request
  │
  ▼
Redis GET key
  ├─ HIT  → return cached JSON immediately
  └─ MISS → query MySQL
              │
              ▼
            store result in Redis with TTL
              │
              ▼
            return JSON to client
```

Redis keys used:

| Key pattern | TTL |
|---|---|
| `campaign:{id}:performance` | 30 seconds |
| `advertiser:{id}:spending` | 300 seconds (5 min) |
| `user:{id}:engagements` | 60 seconds |

---

## Cleanup

Stop and remove containers (keeps the MySQL volume intact):

```bash
docker compose down
```

To also flush Redis cache manually:

```bash
docker exec redis_hw5 redis-cli FLUSHALL
```
