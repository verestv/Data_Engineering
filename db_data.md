mysql> show tables;
+---------------------+
| Tables_in_adtech_db |
+---------------------+
| ad_slots            |
| advertisers         |
| campaigns           |
| clicks              |
| impressions         |
| user_interests      |
| users               |
+---------------------+
7 rows in set (0.01 sec)

mysql> SELECT * FROM advertisers LIMIT 10;
+---------------+----------------+
| advertiser_id | name           |
+---------------+----------------+
 |            1 | Advertiser_30
 |            2 | Advertiser_25
 |            3 | Advertiser_95
 |            4 | Advertiser_53
  |           5 | Advertiser_5
 |            6 | Advertiser_99
 |            7 | Advertiser_34
 |            8 | Advertiser_66
 |            9 | Advertiser_45
 |           10 | Advertiser_22
+---------------+----------------+
10 rows in set (0.01 sec)

mysql> SELECT * FROM users LIMIT 10;
+---------+------+--------+-----------+-------------+
| user_id | age  | gender | location  | signup_date |
+---------+------+--------+-----------+-------------+
|       1 |   58 | Male   | USA       | 2020-07-28  |
|       2 |   61 | Male   | Australia | 2021-04-21  |
|       3 |   50 | Male   | Australia | 2022-07-08  |
|       4 |   55 | Female | USA       | 2021-07-23  |
|       5 |   27 | Male   | Germany   | 2022-02-17  |
|       6 |   24 | Female | Germany   | 2023-01-03  |
|       7 |   25 | Female | USA       | 2023-12-13  |
|       8 |   22 | Male   | UK        | 2020-07-25  |
|       9 |   42 | Female | India     | 2021-03-05  |
|      10 |   60 | Female | USA       | 2022-08-04  |
+---------+------+--------+-----------+-------------+
10 rows in set (0.20 sec)

mysql> SELECT * FROM user_interests LIMIT 10;
+----+---------+-------------+
| id | user_id | interest    |
+----+---------+-------------+
     |       1 | Gaming
     |       1 | Sports
     |       1 | Health
 | 4 |       2 | Technology
  |5 |       2 | Education
     |       2 | Health
     |       2 | Sports
     |       3 | Health
     |       3 | Sports
     |       4 | Health
+----+---------+-------------+
10 rows in set (0.04 sec)

mysql> 
