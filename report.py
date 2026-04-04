import os
import json
import mysql.connector
import pandas as pd
from datetime import datetime

# ── Config (all from environment variables — never hardcode passwords) ──────
DB_CONFIG = {
    "host": os.getenv("DB_HOST", "127.0.0.1"),
    "port": int(os.getenv("DB_PORT", "3306")),
    "user": os.getenv("DB_USER", "root"),
    "password": os.getenv("DB_PASSWORD", ""),
    "database": os.getenv("DB_NAME", "adtech_db"),
}

START_DATE = "2024-01-01"
END_DATE   = "2024-01-31"
OUTPUT_DIR = "reports"
os.makedirs(OUTPUT_DIR, exist_ok=True)

# ── Queries ─────────────────────────────────────────────────────────────────
QUERIES = {
    "q1_top_ctr_campaigns": {
        "title": "Q1 — Top 5 Campaigns by CTR",
        "sql": f"""
            SELECT
                c.campaign_name,
                a.advertiser_name,
                COUNT(i.impression_id)                                    AS impressions,
                COUNT(cl.click_id)                                        AS clicks,
                ROUND(COUNT(cl.click_id)*100.0/COUNT(i.impression_id), 4) AS ctr_pct
            FROM impressions i
            JOIN campaigns   c  ON c.campaign_id   = i.campaign_id
            JOIN advertisers a  ON a.advertiser_id = c.advertiser_id
            LEFT JOIN clicks cl ON cl.impression_id = i.impression_id
            WHERE i.event_timestamp BETWEEN '{START_DATE}' AND '{END_DATE}'
            GROUP BY i.campaign_id, c.campaign_name, a.advertiser_name
            HAVING COUNT(i.impression_id) > 0
            ORDER BY ctr_pct DESC
            LIMIT 5
        """,
    },
    "q2_advertiser_spend": {
        "title": "Q2 — Top Advertiser Spenders",
        "sql": f"""
            SELECT
                a.advertiser_name,
                COUNT(i.impression_id)                                          AS impressions,
                COUNT(cl.click_id)                                              AS clicks,
                ROUND(COUNT(cl.click_id)*100.0/COUNT(i.impression_id), 4)      AS ctr_pct,
                ROUND(SUM(i.ad_cost), 2)                                        AS total_spend,
                ROUND(COALESCE(SUM(cl.ad_revenue), 0), 2)                      AS total_revenue,
                ROUND(COALESCE(SUM(cl.ad_revenue),0)/NULLIF(SUM(i.ad_cost),0), 4) AS roas
            FROM impressions i
            JOIN campaigns   c  ON c.campaign_id   = i.campaign_id
            JOIN advertisers a  ON a.advertiser_id = c.advertiser_id
            LEFT JOIN clicks cl ON cl.impression_id = i.impression_id
            WHERE i.event_timestamp BETWEEN '{START_DATE}' AND '{END_DATE}'
            GROUP BY a.advertiser_id, a.advertiser_name
            ORDER BY total_spend DESC
            LIMIT 10
        """,
    },
    "q3_cpc_cpm": {
        "title": "Q3 — CPC and CPM per Campaign",
        "sql": f"""
            SELECT
                c.campaign_name,
                a.advertiser_name,
                COUNT(i.impression_id)                                       AS impressions,
                COUNT(cl.click_id)                                           AS clicks,
                ROUND(SUM(i.ad_cost), 2)                                     AS total_spend,
                ROUND(SUM(i.ad_cost)/NULLIF(COUNT(cl.click_id),0), 4)       AS cpc,
                ROUND(SUM(i.ad_cost)*1000.0/COUNT(i.impression_id), 4)      AS cpm
            FROM impressions i
            JOIN campaigns   c  ON c.campaign_id   = i.campaign_id
            JOIN advertisers a  ON a.advertiser_id = c.advertiser_id
            LEFT JOIN clicks cl ON cl.impression_id = i.impression_id
            WHERE i.event_timestamp BETWEEN '{START_DATE}' AND '{END_DATE}'
            GROUP BY i.campaign_id, c.campaign_name, a.advertiser_name
            HAVING COUNT(i.impression_id) > 0
            ORDER BY cpc ASC
        """,
    },
    "q4_revenue_by_country": {
        "title": "Q4 — Top Countries by Ad Revenue",
        "sql": f"""
            SELECT
                co.country_name,
                COUNT(i.impression_id)                                          AS impressions,
                COUNT(cl.click_id)                                              AS clicks,
                ROUND(COUNT(cl.click_id)*100.0/COUNT(i.impression_id), 4)      AS ctr_pct,
                ROUND(SUM(i.ad_cost), 2)                                        AS total_spend,
                ROUND(COALESCE(SUM(cl.ad_revenue), 0), 2)                      AS total_revenue,
                ROUND(COALESCE(SUM(cl.ad_revenue),0)/NULLIF(SUM(i.ad_cost),0), 4) AS roas
            FROM impressions i
            JOIN countries co   ON co.country_id   = i.served_country_id
            LEFT JOIN clicks cl ON cl.impression_id = i.impression_id
            WHERE i.event_timestamp BETWEEN '{START_DATE}' AND '{END_DATE}'
            GROUP BY i.served_country_id, co.country_name
            ORDER BY total_revenue DESC
            LIMIT 20
        """,
    },
    "q5_top_users": {
        "title": "Q5 — Top 10 Most Engaged Users",
        "sql": f"""
            SELECT
                i.user_id,
                u.age,
                u.gender,
                co.country_name,
                COUNT(i.impression_id)                                       AS impressions_served,
                COUNT(cl.click_id)                                           AS total_clicks,
                ROUND(COUNT(cl.click_id)*100.0/COUNT(i.impression_id), 4)   AS personal_ctr_pct
            FROM impressions i
            JOIN users      u   ON u.user_id       = i.user_id
            JOIN countries  co  ON co.country_id   = u.country_id
            LEFT JOIN clicks cl ON cl.impression_id = i.impression_id
            WHERE i.event_timestamp BETWEEN '{START_DATE}' AND '{END_DATE}'
            GROUP BY i.user_id, u.age, u.gender, co.country_name
            HAVING COUNT(cl.click_id) > 0
            ORDER BY total_clicks DESC
            LIMIT 10
        """,
    },
    "q6_budget_consumption": {
        "title": "Q6 — Campaigns Above 80% Budget Spent",
        "sql": """
            SELECT
                c.campaign_name,
                a.advertiser_name,
                ROUND(c.budget, 2)                                          AS budget,
                ROUND(COALESCE(SUM(i.ad_cost), 0), 2)                      AS total_spent,
                ROUND(c.budget - COALESCE(SUM(i.ad_cost), 0), 2)           AS remaining_budget,
                ROUND(COALESCE(SUM(i.ad_cost),0)/c.budget*100, 2)          AS pct_spent
            FROM campaigns   c
            JOIN advertisers a  ON a.advertiser_id = c.advertiser_id
            LEFT JOIN impressions i ON i.campaign_id = c.campaign_id
            GROUP BY c.campaign_id, c.campaign_name, a.advertiser_name,
                     c.campaign_start_date, c.campaign_end_date, c.budget
            HAVING pct_spent >= 80
            ORDER BY pct_spent DESC
        """,
    },
    "q7_device_ctr": {
        "title": "Q7 — CTR by Device Type",
        "sql": f"""
            SELECT
                i.device,
                COUNT(i.impression_id)                                          AS impressions,
                COUNT(cl.click_id)                                              AS clicks,
                ROUND(COUNT(cl.click_id)*100.0/COUNT(i.impression_id), 4)      AS ctr_pct,
                ROUND(SUM(i.ad_cost), 2)                                        AS total_spend,
                ROUND(SUM(i.ad_cost)/NULLIF(COUNT(cl.click_id),0), 4)          AS avg_cpc,
                ROUND(COUNT(i.impression_id)*100.0
                      / SUM(COUNT(i.impression_id)) OVER (), 2)                AS pct_of_total_impressions
            FROM impressions i
            LEFT JOIN clicks cl ON cl.impression_id = i.impression_id
            WHERE i.event_timestamp BETWEEN '{START_DATE}' AND '{END_DATE}'
            GROUP BY i.device
            ORDER BY ctr_pct DESC
        """,
    },
}

# ── Runner ───────────────────────────────────────────────────────────────────
def run_all():
    print(f"Connecting to MySQL at {DB_CONFIG['host']}:{DB_CONFIG['port']} ...")
    conn = mysql.connector.connect(**DB_CONFIG)
    print("Connected.\n")

    all_results = {}
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

    for key, q in QUERIES.items():
        print(f"Running {q['title']} ...")
        try:
            df = pd.read_sql(q["sql"], conn)
            csv_path = os.path.join(OUTPUT_DIR, f"{key}.csv")
            df.to_csv(csv_path, index=False)
            print(df.to_string(index=False))
            print(f"  -> saved {len(df)} rows to {csv_path}\n")
            all_results[key] = {
                "title":   q["title"],
                "rows":    len(df),
                "columns": list(df.columns),
                "data":    df.to_dict(orient="records"),
            }
        except Exception as e:
            print(f"  ERROR: {e}\n")
            all_results[key] = {"title": q["title"], "error": str(e)}

    conn.close()

    json_path = os.path.join(OUTPUT_DIR, f"report_{timestamp}.json")
    with open(json_path, "w") as f:
        json.dump(all_results, f, indent=2, default=str)

    print(f"Full JSON report -> {json_path}")
    print("Done.")


if __name__ == "__main__":
    run_all()
