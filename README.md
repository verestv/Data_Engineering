# Project Setup

## 1. Datasets

We have two datasets: `users.csv` and `ad_events_header_updated.csv`.
They can be read with [read_csv.py](read_csv.py) (prints the first 15 rows to see the layout).

## 2. Relational Schema

The visual relational schema is provided in [db_schema.png](db_schema.png).

## 3. DDL Scripts

DDL scripts with additional explanation are located in [ddl_scripts.sql](init/ddl_scripts.sql) — placed in the `init/` folder so they run automatically when the Docker image is created.

## 4. Naming Conventions

According to best practices, we use lowercase for table and column names. Headers in `users.csv` were renamed manually; headers in `ad_events_header_updated.csv` were renamed using [change_csv_headers.py](change_csv_headers.py).

## 5. Splitting CSV Files

We split the original CSV files into separate files so that each contains only the columns needed for a specific table. Script: [build_csvs.py](build_csvs.py).

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

Bring up the database using [docker-compose.yml](docker-compose.yml), which creates the necessary MySQL Docker image/container.

## 7. Copying CSV Files into Docker

For better performance, copy the generated CSV files into the Docker container. For example:

```bash
docker cp countries.csv adtech_mysql:/var/lib/mysql-files/countries.csv
```

Repeat for each CSV file.

## 8. Loading Data into SQL Tables

Each CSV file is loaded into its corresponding table using `LOAD DATA INFILE`. Exact commands are in [load_all.sql](load_all.sql).

It is better to run these commands one by one directly in MySQL to monitor the loading of each table. Log in to MySQL inside the container with:

```bash
docker exec -it adtech_mysql mysql -uroot -prootpass adtech_db
```

## 9. Verifying Data

`SELECT` statements to verify that data has been loaded successfully are in [select_from_tables.txt](select_from_tables.txt).
