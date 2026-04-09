Query 1: Write a CQL query to fetch the CTR per campaign per day.

SELECT
    campaign_id,
    campaign_name,
    advertiser_name,
    event_date,
    total_impressions,
    total_clicks,
    ctr
FROM campaign_daily_stats
WHERE campaign_id = 166
  AND event_date >= '2024-11-01'
  AND event_date <= '2024-11-30';

result: 

   campaign_id | campaign_name | advertiser_name | event_date | total_impressions | total_clicks | ctr
-------------+---------------+-----------------+------------+-------------------+--------------+----------
         166 |  Campaign_387 |   Advertiser_40 | 2024-11-15 |               350 |           11 | 0.031429
         166 |  Campaign_387 |   Advertiser_40 | 2024-11-14 |               307 |           18 | 0.058632
         166 |  Campaign_387 |   Advertiser_40 | 2024-11-13 |               341 |           20 | 0.058651
         166 |  Campaign_387 |   Advertiser_40 | 2024-11-12 |               344 |            9 | 0.026163
         166 |  Campaign_387 |   Advertiser_40 | 2024-11-11 |               314 |           15 | 0.047771
         166 |  Campaign_387 |   Advertiser_40 | 2024-11-10 |               323 |           18 | 0.055728
         166 |  Campaign_387 |   Advertiser_40 | 2024-11-09 |               301 |           18 | 0.059801
         166 |  Campaign_387 |   Advertiser_40 | 2024-11-08 |               303 |           19 | 0.062706
         166 |  Campaign_387 |   Advertiser_40 | 2024-11-07 |               307 |           23 | 0.074919
         166 |  Campaign_387 |   Advertiser_40 | 2024-11-06 |               314 |           16 | 0.050955
         166 |  Campaign_387 |   Advertiser_40 | 2024-11-05 |               282 |           10 | 0.035461
         166 |  Campaign_387 |   Advertiser_40 | 2024-11-04 |               314 |           11 | 0.035032
         166 |  Campaign_387 |   Advertiser_40 | 2024-11-03 |               315 |           12 | 0.038095
         166 |  Campaign_387 |   Advertiser_40 | 2024-11-02 |               291 |           19 | 0.065292
         166 |  Campaign_387 |   Advertiser_40 | 2024-11-01 |               345 |           15 | 0.043478

(15 rows)
cqlsh:adtech> 