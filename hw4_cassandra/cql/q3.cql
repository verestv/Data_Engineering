Query 3: Given a UserID, retrieve the last 10 ads the user saw and whether they clicked.

cqlsh:adtech> SELECT
          ...     user_id,
          ...     event_timestamp,
          ...     campaign_name,
          ...     advertiser_name,
          ...     ad_slot_size,
          ...     device,
          ...     was_clicked,
          ...     click_timestamp,
          ...     ad_revenue,
          ...     ad_cost
          ... FROM user_ad_history
          ... WHERE user_id = 583398
          ... LIMIT 10;

 user_id | event_timestamp                 | campaign_name | advertiser_name | ad_slot_size | device | was_clicked | click_timestamp | ad_revenue | ad_cost
---------+---------------------------------+---------------+-----------------+--------------+--------+-------------+-----------------+------------+---------
  583398 | 2024-12-05 21:28:35.000000+0000 |  Campaign_529 |   Advertiser_53 |      300x250 | Tablet |       False |            null |        0.0 |    1.32
  583398 | 2024-12-02 15:30:50.000000+0000 |  Campaign_240 |   Advertiser_25 |      160x600 | Mobile |       False |            null |        0.0 |    2.13
  583398 | 2024-11-27 14:31:55.000000+0000 |  Campaign_354 |   Advertiser_37 |      300x250 | Mobile |       False |            null |        0.0 |    0.68
  583398 | 2024-11-18 00:44:22.000000+0000 |  Campaign_969 |   Advertiser_97 |      160x600 | Tablet |       False |            null |        0.0 |    1.54
  583398 | 2024-11-16 15:19:08.000000+0000 |  Campaign_611 |   Advertiser_60 |      300x250 | Tablet |       False |            null |        0.0 |    2.85
  583398 | 2024-11-14 16:41:34.000000+0000 |  Campaign_435 |   Advertiser_45 |      300x250 | Tablet |       False |            null |        0.0 |    3.51
  583398 | 2024-11-08 23:38:52.000000+0000 |   Campaign_78 |    Advertiser_9 |       728x90 | Mobile |       False |            null |        0.0 |    1.58
  583398 | 2024-11-08 17:40:45.000000+0000 |  Campaign_237 |   Advertiser_25 |       728x90 | Tablet |       False |            null |        0.0 |    0.48
  583398 | 2024-11-08 02:36:57.000000+0000 |  Campaign_137 |   Advertiser_14 |      300x250 | Tablet |       False |            null |        0.0 |    3.53
  583398 | 2024-10-31 16:54:18.000000+0000 |  Campaign_642 |   Advertiser_64 |       728x90 | Tablet |       False |            null |        0.0 |    3.19

(10 rows)
cqlsh:adtech>

