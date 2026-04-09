# Homework 4 – Ad Performance Analytics with Cassandra

The dataset is the same proccessed CSV files from previous hws

---

## Folder Structure

- `docker-compose.yml`  
  creates Cassandra container

- `cql/01_keyspace_and_schema.cql`  
  CQL script that creates the `adtech` keyspace and all 5 denormalized tables designed for the required business queries

- `cql/q1.cql` – `q5.cql`  
  CQL files with the business queries

- `scripts/load_to_cassandra.py`  
  Python ETL script that:
  - loads the same CSVs used earlier,
  - builds lookup dictionaries for campaigns, advertisers and countries,
  - builds `clicks_by_impression` from `clicks.csv`,
  - streams `impressions.csv` in chunks,
  - inserts denormalized rows into Cassandra tables

---

## Start Cassandra

```bash
docker compose up -d
```
---

## Create Keyspace and Tables

Copy schema file into the container and apply it:

```bash
docker cp cql/01_keyspace_and_schema.cql cassandra_hw4:/tmp/schema.cql
docker exec cassandra_hw4 cqlsh -f /tmp/schema.cql
```

Check created tables:

```bash
docker exec cassandra_hw4 cqlsh -e "USE adtech; DESCRIBE TABLES;"
```

---

## Load Data from CSV

Install dependencies:

```bash
source venv/bin/activate
pip install cassandra-driver pandas pyarrow
```

Run the ETL script:

```bash
cd scripts/
python load_to_cassandra.py
```

This loads data from the same CSV files used in previous homework and inserts them into Cassandra.

---

## Run Queries

Open Cassandra shell:

```bash
docker exec -it cassandra_hw4 cqlsh
```

Then run queries manually from `cql/`

---

## Note about Queries 2, 4 and 5

Queries 2, 4 and 5 use `SUM()` and `GROUP BY` correctly in CQL, but Cassandra cannot sort aggregated values with `ORDER BY total_spend` or `ORDER BY total_clicks`. Because of that, these queries are run in `cqlsh` to aggregate the results, and then the output is sorted outside CQL using bash (`sort`) to show the real top 5 / top 10.
