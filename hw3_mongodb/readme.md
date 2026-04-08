# Homework 3 – MongoDB User Engagement Tracking

This repository implements a MongoDB‑based user engagement store for an adtech use case. It extends the relational model from Homework 1 by denormalizing ad interactions into per‑user documents, making session and behavior queries fast and join‑free.

---

## Folder Structure

- `docker-compose.yml`  
  creates mongodb container (+ old mysql)

- `create_collectoin_mongo.js`  
  Mongo shell script that creates the `user_engagements` collection with designed schema. It defines user demographics, the `impressions` array, and nested `clicks` array

- `indexes.js`  
  Mongo shell script that creates indexes on key fields inside `impressions` (e.g. timestamp, campaign, advertiser). These indexes are used by the aggregation queries to keep time‑window and advertiser filters efficient.

- `load_to_mongo.py`  
  Python ETL script that:
  - connects to MongoDB,  
  - loads CSVs (users, campaigns, impressions, clicks, etc.),  
  - builds lookup dictionaries (countries, interests, advertisers, campaigns),  
  - inserts base user documents (one per user with demographics + interests + empty `impressions`),  
  - streams `impressions.csv` in chunks and `$push`es denormalized impressions (with embedded clicks) into each user document.  
  This script is the main data‑loading pipeline and is designed to be memory‑efficient.

## Query result files (`init/query_results/1.txt` – `5.txt`)

These files contain the MongoDB queries and example outputs for the five tasks:

1. `1.txt` – Query that returns all ad interactions (impressions and nested clicks) for a specific user.  
2. `2.txt` – Aggregation that retrieves a user’s last 5 “sessions” (impressions) with timestamps and click behavior.  
3. `3.txt` – Time‑windowed aggregation that counts clicks per hour per campaign in a 24‑hour window for a specified advertiser.  
4. `4.txt` – Aggregation that finds users who have seen the same campaign at least 2 times without ever clicking (ad fatigue detection).
5. `5.txt` – Aggregation that computes a user’s top 3 most engaged ad categories based on past clicks (e.g. using `campaign_name` as category).