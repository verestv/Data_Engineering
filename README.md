Here is your text, same content but formatted and cleaned up as Markdown (for `README.md`):

```markdown
We have two datasets: `users.csv` and `ad_events_header_updated.csv`.  
They can be read with a small Python script (in our case we print the first 15 rows to see the layout).

The relational schema and an explanation of the design are provided in the file **relation_schema**.

Then we create DDL scripts (SQL file) with additional explanation.  
According to best practices, we use lowercase for table and column names, so we renamed the headers in both CSV files using a small script.

Next, we need to split the original CSV files into separate CSV files so that each one contains only the necessary data and columns for a specific table.  
For this we use the script: `build_csvs.py`.

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

All CSVs generated. You can now LOAD DATA INFILE into MySQL.
(venv) ivan@DESKTOP-HLUUP8P:~/Data_Eng$
```

After that we need to bring up the database.  
There is a YAML file that creates the necessary MySQL Docker image/container.

For better performance, we copy these generated CSV files into the Docker container.  
For example:

```bash
docker cp countries.csv adtech_mysql:/var/lib/mysql-files/countries.csv
```

and repeat for each CSV file.

Then each CSV file is loaded into its corresponding SQL table using `LOAD DATA INFILE`.  
In our case it is better to run these commands one by one directly in MySQL to monitor loading of each table.

We can log in to MySQL in the container with:

```bash
docker exec -it adtech_mysql mysql -uroot -prootpass adtech_db
```

From there we can run `SELECT` statements to verify that the data has been loaded successfully.
```
