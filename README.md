# Project Setup & Data Pipeline

## 1. Datasets

We have two datasets: `users.csv` and `ad_events_header_updated.csv`.
They can be read with a small Python script read_csv.py (in our case we print the first 15 rows to see the layout).

## 2. Relational Schema

The visual relational schema is provided in the file **db_schema.png**.

## 3. DDL Scripts

We create DDL scripts (SQL file) with additional explanation. -> ddl_sctips.sql

## 4. Naming Conventions

According to best practices, we use lowercase for table and column names, so we renamed the headers in both CSV files using a small script. change_csv_headers.py

## 5. Splitting CSV Files

We need to split the original CSV files into separate CSV files so that each one contains only the necessary data and columns for a specific table. For this we use the script: `build_csvs.py`.

Example run and output:

```text
python3 build_csvs.py
Reading users.csv ...
Building countries ...
countries.csv written with 5 rows
Building interests ...
interests.csv written with 8 rows
Building users_fact ...
users_fact.csv written with 700000 rows
Building user_interests ...
user_interests.csv written with 1748972 rows
Reading ad_events_header_updated.csv ...
Building advertisers ...
advertisers.csv written with 100 rows
Mapping countries and interests on adtech ...
Found 5 new countries from adtech, appending ...
Found 8 new interests from adtech, appending ...
Building campaigns ...
campaigns.csv written with 1013 rows
Building campaign_targeting ...
campaign_targeting.csv written with 1013 rows
Building ad_events ...
ad_events.csv written with 10000000 rows
All CSVs generated.
```

## 6. Database Setup

After that we need to bring up the database. There is a docker-compose.yml file that creates the necessary MySQL Docker image/container. 

## 7. Copying CSV Files into Docker

For better performance, we copy the generated CSV files into the Docker container. For example:

```bash
docker cp countries.csv adtech_mysql:/var/lib/mysql-files/countries.csv
```

Repeat this command for each CSV file.

## 8. Loading Data into SQL Tables

Each CSV file is loaded into its corresponding SQL table using `LOAD DATA INFILE`. (Exact commands are in the SQL file load_all.sql)

It is better to run these commands one by one directly in MySQL to monitor the loading of each table. Log in to MySQL inside the container with:

```bash
docker exec -it adtech_mysql mysql -uroot -prootpass adtech_db
```

## 9. Verifying Data

Use `SELECT` statements to verify that the data has been loaded successfully -> located in select_from_tables.txt
