Query 4: Retrieve the top 10 users with the highest number of ad clicks in the past 30 days.

ivan@DESKTOP-HLUUP8P:~/Data_Eng$ echo "user_id | total_clicks" && echo "---------+--------------" && \
docker exec -it cassandra_hw4 cqlsh --no-color -e "
USE adtech;
SELECT user_id, SUM(click_count) AS total_clicks
FROM user_click_counts
WHERE bucket = 1
  AND event_date >= '2024-11-01'
  AND event_date <= '2024-11-30'
GROUP BY bucket, user_id
ALLOW FILTERING;
" | grep '|' | grep -v 'user_id\|--' | sort -t'|' -k2 -rn | head -10
user_id | total_clicks
---------+--------------
  531792 |            6
  652388 |            5
  628310 |            5
  611056 |            5
  528991 |            5
  416579 |            5
  371342 |            5
  252095 |            5
   52152 |            5
   24620 |            5
ivan@DESKTOP-HLUUP8P:~/Data_Eng$