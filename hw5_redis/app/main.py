from fastapi import FastAPI, HTTPException
from decimal import Decimal
import database as db
import cache

app = FastAPI(title="AdTech Analytics API", version="1.0.0")

# ── TTLs ──────────────────────────────────────────────────────────────────────
TTL_CAMPAIGN   = 30    # seconds
TTL_ADVERTISER = 300   # 5 minutes
TTL_USER       = 60    # 1 minute


# ── helpers ───────────────────────────────────────────────────────────────────
def to_serializable(rows: list[dict]) -> list[dict]:
    """Convert Decimal → float so json.dumps works."""
    result = []
    for row in rows:
        result.append({
            k: float(v) if isinstance(v, Decimal) else v
            for k, v in row.items()
        })
    return result


# ── GET /campaign/{campaign_id}/performance ───────────────────────────────────
@app.get("/campaign/{campaign_id}/performance")
def campaign_performance(campaign_id: int):
    key = f"campaign:{campaign_id}:performance"

    cached = cache.cache_get(key)
    if cached:
        cached["cache"] = "HIT"
        return cached

    sql = """
        SELECT
            c.campaign_id,
            c.campaign_name,
            a.advertiser_name,
            COUNT(DISTINCT i.impression_id)                          AS total_impressions,
            COUNT(DISTINCT cl.click_id)                              AS total_clicks,
            ROUND(
                COUNT(DISTINCT cl.click_id) /
                NULLIF(COUNT(DISTINCT i.impression_id), 0) * 100, 4
            )                                                        AS ctr_percent,
            ROUND(SUM(i.ad_cost), 2)                                 AS total_ad_spend
        FROM campaigns c
        JOIN advertisers a  ON a.advertiser_id  = c.advertiser_id
        LEFT JOIN impressions i  ON i.campaign_id  = c.campaign_id
        LEFT JOIN clicks cl      ON cl.impression_id = i.impression_id
        WHERE c.campaign_id = %s
        GROUP BY c.campaign_id, c.campaign_name, a.advertiser_name
    """
    rows = db.query(sql, (campaign_id,))
    if not rows:
        raise HTTPException(status_code=404, detail="Campaign not found")

    data = to_serializable(rows)[0]
    cache.cache_set(key, data, TTL_CAMPAIGN)
    data["cache"] = "MISS"
    return data


# ── GET /advertiser/{advertiser_id}/spending ──────────────────────────────────
@app.get("/advertiser/{advertiser_id}/spending")
def advertiser_spending(advertiser_id: int):
    key = f"advertiser:{advertiser_id}:spending"

    cached = cache.cache_get(key)
    if cached:
        cached["cache"] = "HIT"
        return cached

    sql = """
        SELECT
            a.advertiser_id,
            a.advertiser_name,
            COUNT(DISTINCT c.campaign_id)    AS total_campaigns,
            COUNT(DISTINCT i.impression_id)  AS total_impressions,
            COUNT(DISTINCT cl.click_id)      AS total_clicks,
            ROUND(SUM(i.ad_cost), 2)         AS total_ad_spend,
            ROUND(SUM(cl.ad_revenue), 2)     AS total_ad_revenue
        FROM advertisers a
        LEFT JOIN campaigns c    ON c.advertiser_id  = a.advertiser_id
        LEFT JOIN impressions i  ON i.campaign_id    = c.campaign_id
        LEFT JOIN clicks cl      ON cl.impression_id = i.impression_id
        WHERE a.advertiser_id = %s
        GROUP BY a.advertiser_id, a.advertiser_name
    """
    rows = db.query(sql, (advertiser_id,))
    if not rows:
        raise HTTPException(status_code=404, detail="Advertiser not found")

    data = to_serializable(rows)[0]
    cache.cache_set(key, data, TTL_ADVERTISER)
    data["cache"] = "MISS"
    return data


# ── GET /user/{user_id}/engagements ──────────────────────────────────────────
@app.get("/user/{user_id}/engagements")
def user_engagements(user_id: int):
    key = f"user:{user_id}:engagements"

    cached = cache.cache_get(key)
    if cached:
        cached["cache"] = "HIT"
        return cached

    sql = """
        SELECT
            i.impression_id,
            i.event_timestamp,
            c.campaign_name,
            a.advertiser_name,
            i.ad_slot_size,
            i.device,
            co.country_name                                   AS served_country,
            i.ad_cost,
            CASE WHEN cl.click_id IS NOT NULL THEN 1 ELSE 0 END AS was_clicked,
            cl.click_timestamp,
            cl.ad_revenue
        FROM impressions i
        JOIN campaigns   c   ON c.campaign_id    = i.campaign_id
        JOIN advertisers a   ON a.advertiser_id  = c.advertiser_id
        JOIN countries   co  ON co.country_id    = i.served_country_id
        LEFT JOIN clicks cl  ON cl.impression_id = i.impression_id
        WHERE i.user_id = %s
        ORDER BY i.event_timestamp DESC
        LIMIT 20
    """
    rows = db.query(sql, (user_id,))
    if not rows:
        raise HTTPException(status_code=404, detail="User not found or no engagements")

    data = {
        "user_id": user_id,
        "total_returned": len(rows),
        "engagements": to_serializable(rows),
    }
    cache.cache_set(key, data, TTL_USER)
    data["cache"] = "MISS"
    return data


# ── health ────────────────────────────────────────────────────────────────────
@app.get("/health")
def health():
    return {"status": "ok"}
