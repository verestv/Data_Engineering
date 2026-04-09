import os
import sys
import math
import time
from datetime import datetime, date
from decimal import Decimal

import pandas as pd
from dotenv import load_dotenv
from cassandra.cluster import Cluster
from cassandra import ConsistencyLevel
from cassandra.concurrent import execute_concurrent_with_args

# ── Load .env (optional, same pattern as Mongo loader) ───────────────────────
load_dotenv()
load_dotenv(dotenv_path=os.path.join("..", ".env"))

# ── Config ────────────────────────────────────────────────────────────────────
CSV_DIR          = os.environ.get("CSV_DIR", "../../csv_files_v2")
CASSANDRA_HOST   = os.environ.get("CASSANDRA_HOST", "127.0.0.1")
CASSANDRA_PORT   = int(os.environ.get("CASSANDRA_PORT", "9042"))
KEYSPACE         = "adtech"
CHUNK_SIZE       = 100_000   # same as Mongo loader
CONCURRENCY      = 50        # parallel async Cassandra writes per batch


# ── Helpers ───────────────────────────────────────────────────────────────────
def fmt_time(seconds):
    if seconds < 60:
        return f"{seconds:.0f}s"
    m, s = divmod(int(seconds), 60)
    if m < 60:
        return f"{m}m {s}s"
    h, m = divmod(m, 60)
    return f"{h}h {m}m {s}s"


def progress_bar(current, total, width=30, prefix="", extra=""):
    pct = current / total if total else 0
    filled = int(width * pct)
    bar = "█" * filled + "░" * (width - filled)
    line = f"\r  {prefix}|{bar}| {pct:5.1%}  {current:,}/{total:,}  {extra}"
    sys.stdout.write(line)
    sys.stdout.flush()


def safe_decimal(val):
    """float / NaN / None → Decimal or None."""
    try:
        if val is None or (isinstance(val, float) and math.isnan(val)):
            return None
        return Decimal(str(val))
    except Exception:
        return None


def safe_datetime(val):
    """pandas Timestamp / NaT / None / '' → Python datetime or None."""
    if val is None:
        return None
    if isinstance(val, str):
        val = val.strip()
        if val == "":
            return None
        try:
            return datetime.fromisoformat(val)
        except ValueError:
            return None
    try:
        if pd.isna(val):
            return None
    except Exception:
        pass
    if isinstance(val, pd.Timestamp):
        return val.to_pydatetime()
    return val


def load_csv(name, **kwargs):
    path = os.path.join(CSV_DIR, name)
    if not os.path.exists(path):
        print(f"  ✗ {name} not found at {path}")
        sys.exit(1)
    print(f"  Loading {name}...", end=" ", flush=True)
    t = time.time()
    df = pd.read_csv(path, engine="pyarrow", **kwargs)
    print(f"{len(df):,} rows ({time.time()-t:.1f}s)")
    return df


# ── Connect ───────────────────────────────────────────────────────────────────
def connect():
    print(f"\n═══ Connecting to Cassandra {CASSANDRA_HOST}:{CASSANDRA_PORT} ═══")
    cluster = Cluster(
        contact_points=[CASSANDRA_HOST],
        port=CASSANDRA_PORT,
        connect_timeout=30,
    )
    session = cluster.connect(KEYSPACE)
    session.default_consistency_level = ConsistencyLevel.LOCAL_ONE
    print("  ✓ Connected")
    return cluster, session


# ── Prepare all statements once ───────────────────────────────────────────────
def prepare_statements(session):
    return {
        "campaign_daily_stats": session.prepare("""
            INSERT INTO campaign_daily_stats
                (campaign_id, event_date, campaign_name, advertiser_name,
                 total_impressions, total_clicks, total_cost, ctr)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """),
        "advertiser_spend_by_day": session.prepare("""
            INSERT INTO advertiser_spend_by_day
                (bucket, advertiser_id, event_date, advertiser_name, daily_spend)
            VALUES (?, ?, ?, ?, ?)
        """),
        "user_ad_history": session.prepare("""
            INSERT INTO user_ad_history
                (user_id, event_timestamp, impression_id, campaign_id,
                 campaign_name, advertiser_name, ad_slot_size, device,
                 was_clicked, click_timestamp, ad_revenue, ad_cost)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """),
        "user_click_counts": session.prepare("""
            INSERT INTO user_click_counts
                (bucket, user_id, event_date, click_count)
            VALUES (?, ?, ?, ?)
        """),
        "advertiser_spend_by_region": session.prepare("""
            INSERT INTO advertiser_spend_by_region
                (country_name, advertiser_id, event_date, advertiser_name, daily_spend)
            VALUES (?, ?, ?, ?, ?)
        """),
    }


# ── Bulk insert helper ────────────────────────────────────────────────────────
def bulk_insert(session, stmt, params):
    if not params:
        return 0
    results = execute_concurrent_with_args(session, stmt, params, concurrency=CONCURRENCY)
    return sum(1 for ok, _ in results if not ok)


# ── Main ──────────────────────────────────────────────────────────────────────
def main():
    t_start = time.time()

    # ─── 1. Load lookup CSVs ──────────────────────────────────────────────────
    print("\n═══ Loading lookup CSVs ═══")
    advertisers      = load_csv("advertisers.csv")
    campaigns        = load_csv("campaigns.csv")
    countries        = load_csv("countries.csv")
    # loaded but not used in Cassandra tables (available for future use)
    _users           = load_csv("users_fact.csv")
    _interests       = load_csv("interests.csv")
    _user_interests  = load_csv("user_interests.csv")
    _camp_targeting  = load_csv("campaign_targeting.csv")

    # ─── 2. Build lookup dicts ────────────────────────────────────────────────
    print("\n═══ Building lookup dictionaries ═══")

    # country_id → country_name
    country_map = dict(zip(countries["country_id"], countries["country_name"]))

    # campaign_id → campaign_name, advertiser_id, advertiser_name
    camp_merged       = campaigns.merge(advertisers, on="advertiser_id", how="left")
    campaign_name_map = dict(zip(camp_merged["campaign_id"], camp_merged["campaign_name"]))
    campaign_adv_id   = dict(zip(camp_merged["campaign_id"], camp_merged["advertiser_id"]))
    campaign_adv_name = dict(zip(camp_merged["campaign_id"], camp_merged["advertiser_name"]))

    print(f"  ✓ {len(country_map):,} countries, {len(campaign_name_map):,} campaigns")

    # ─── 3. Build clicks index ────────────────────────────────────────────────
    # Exactly like Mongo loader: clicks_by_imp[impression_id] → click record
    # clicks.csv columns: click_id, impression_id, click_timestamp, ad_revenue
    print("\n═══ Building clicks index ═══")
    t_clicks = time.time()

    clicks_df = load_csv("clicks.csv")
    clicks_df["click_timestamp"] = pd.to_datetime(
        clicks_df["click_timestamp"], errors="coerce"
    )

    clicks_by_imp = {}
    for row in clicks_df.itertuples(index=False):
        imp_id = str(row.impression_id)
        clicks_by_imp[imp_id] = {
            "click_id":        str(row.click_id),
            "click_timestamp": safe_datetime(row.click_timestamp),
            "ad_revenue":      float(row.ad_revenue) if pd.notna(row.ad_revenue) else 0.0,
        }

    del clicks_df
    print(f"  ✓ {len(clicks_by_imp):,} impressions have clicks ({fmt_time(time.time()-t_clicks)})")

    # ─── 4. Connect + prepare ─────────────────────────────────────────────────
    cluster, session = connect()
    stmts = prepare_statements(session)

    # ─── 5. Stream impressions.csv ────────────────────────────────────────────
    imp_path = os.path.join(CSV_DIR, "impressions.csv")
    print(f"\n═══ Processing impressions.csv in {CHUNK_SIZE:,}-row chunks ═══")

    print("  Counting rows...", end=" ", flush=True)
    with open(imp_path, "r") as f:
        total_rows = sum(1 for _ in f) - 1
    total_chunks = (total_rows + CHUNK_SIZE - 1) // CHUNK_SIZE
    print(f"{total_rows:,} rows ({total_chunks} chunks)")

    total_imp   = 0
    chunk_num   = 0
    chunk_times = []

    # Running accumulators for aggregated tables (built per-chunk, flushed per-chunk)
    # We use dicts keyed by grouping tuple to accumulate within a chunk,
    # then insert at end of each chunk (avoids UPDATE logic in Cassandra).
    # Since Cassandra INSERT is upsert, running same key twice just overwrites —
    # so we track totals across ALL chunks in memory (small: campaigns × days).
    agg_campaign_day    = {}   # (campaign_id, date) → {impressions, clicks, cost}
    agg_adv_day         = {}   # (advertiser_id, date) → {spend, adv_name}
    agg_user_clicks_day = {}   # (user_id, date) → click_count
    agg_region_day      = {}   # (country_name, advertiser_id, date) → {spend, adv_name}

    try:
        for chunk in pd.read_csv(
            imp_path,
            chunksize=CHUNK_SIZE,
            engine="c",
            dtype={
                "impression_id":    str,
                "campaign_id":      "Int64",
                "user_id":          "Int64",
                "ad_slot_size":     str,
                "device":           str,
                "served_country_id":"Int64",
                "bid_amount":       float,
                "ad_cost":          float,
            },
            parse_dates=["event_timestamp"],
        ):
            chunk_num  += 1
            t_chunk     = time.time()
            total_imp  += len(chunk)

            # ── Per-row: TABLE 3 (user_ad_history) params + accumulate aggregates ──
            t3_params = []

            for row in chunk.itertuples(index=False):
                imp_id  = str(row.impression_id)
                camp_id = int(row.campaign_id)
                uid     = int(row.user_id)
                ts      = safe_datetime(row.event_timestamp)
                edate   = ts.date() if ts else None
                cost    = float(row.ad_cost) if pd.notna(row.ad_cost) else 0.0

                camp_name = str(campaign_name_map.get(camp_id, "Unknown"))
                adv_id    = int(campaign_adv_id.get(camp_id, 0))
                adv_name  = str(campaign_adv_name.get(camp_id, "Unknown"))
                country   = str(country_map.get(int(row.served_country_id), "Unknown"))

                click_info  = clicks_by_imp.get(imp_id)
                was_clicked = click_info is not None
                click_ts    = click_info["click_timestamp"] if click_info else None
                ad_revenue  = click_info["ad_revenue"]      if click_info else 0.0

                # ── TABLE 3: user_ad_history (row-level) ──
                t3_params.append((
                    uid,
                    ts,
                    imp_id,
                    camp_id,
                    camp_name,
                    adv_name,
                    str(row.ad_slot_size),
                    str(row.device),
                    was_clicked,
                    click_ts,
                    safe_decimal(ad_revenue),
                    safe_decimal(cost),
                ))

                if edate is None:
                    continue

                # ── TABLE 1: campaign_daily_stats accum ──
                k1 = (camp_id, edate)
                if k1 not in agg_campaign_day:
                    agg_campaign_day[k1] = {
                        "camp_name": camp_name, "adv_name": adv_name,
                        "impressions": 0, "clicks": 0, "cost": 0.0,
                    }
                agg_campaign_day[k1]["impressions"] += 1
                agg_campaign_day[k1]["clicks"]      += int(was_clicked)
                agg_campaign_day[k1]["cost"]        += cost

                # ── TABLE 2: advertiser_spend_by_day accum ──
                k2 = (adv_id, edate)
                if k2 not in agg_adv_day:
                    agg_adv_day[k2] = {"adv_name": adv_name, "spend": 0.0}
                agg_adv_day[k2]["spend"] += cost

                # ── TABLE 4: user_click_counts accum ──
                if was_clicked:
                    k4 = (uid, edate)
                    agg_user_clicks_day[k4] = agg_user_clicks_day.get(k4, 0) + 1

                # ── TABLE 5: advertiser_spend_by_region accum ──
                k5 = (country, adv_id, edate)
                if k5 not in agg_region_day:
                    agg_region_day[k5] = {"adv_name": adv_name, "spend": 0.0}
                agg_region_day[k5]["spend"] += cost

            # ── Flush TABLE 3 each chunk (large, row-level) ──
            errs = bulk_insert(session, stmts["user_ad_history"], t3_params)

            elapsed    = time.time() - t_chunk
            chunk_times.append(elapsed)
            avg_chunk  = sum(chunk_times) / len(chunk_times)
            remaining  = (total_chunks - chunk_num) * avg_chunk
            progress_bar(
                chunk_num, total_chunks,
                prefix="Imps: ",
                extra=f"{elapsed:.1f}s/chunk  ETA: {fmt_time(remaining)}  t3_errs={errs}   "
            )

        print(f"\n  ✓ All {total_imp:,} impressions processed")

        # ── Flush aggregated tables (built across all chunks) ─────────────────

        # TABLE 1: campaign_daily_stats
        print("\n═══ Inserting aggregated tables ═══")
        t1_params = []
        for (camp_id, edate), v in agg_campaign_day.items():
            imps  = v["impressions"]
            clicks = v["clicks"]
            ctr   = clicks / imps if imps > 0 else 0.0
            t1_params.append((
                camp_id, edate,
                v["camp_name"], v["adv_name"],
                imps, clicks,
                safe_decimal(v["cost"]),
                ctr,
            ))
        errs = bulk_insert(session, stmts["campaign_daily_stats"], t1_params)
        print(f"  [1] campaign_daily_stats    {len(t1_params):>8,} rows | errors={errs}")

        # TABLE 2: advertiser_spend_by_day
        t2_params = [
            (1, adv_id, edate, v["adv_name"], safe_decimal(v["spend"]))
            for (adv_id, edate), v in agg_adv_day.items()
        ]
        errs = bulk_insert(session, stmts["advertiser_spend_by_day"], t2_params)
        print(f"  [2] advertiser_spend_by_day {len(t2_params):>8,} rows | errors={errs}")

        # TABLE 4: user_click_counts
        t4_params = [
            (1, uid, edate, cnt)
            for (uid, edate), cnt in agg_user_clicks_day.items()
        ]
        errs = bulk_insert(session, stmts["user_click_counts"], t4_params)
        print(f"  [4] user_click_counts       {len(t4_params):>8,} rows | errors={errs}")

        # TABLE 5: advertiser_spend_by_region
        t5_params = [
            (country, adv_id, edate, v["adv_name"], safe_decimal(v["spend"]))
            for (country, adv_id, edate), v in agg_region_day.items()
        ]
        errs = bulk_insert(session, stmts["advertiser_spend_by_region"], t5_params)
        print(f"  [5] advertiser_spend_by_region {len(t5_params):>6,} rows | errors={errs}")

        print(f"\n  Total time: {fmt_time(time.time() - t_start)}")
        print("  ✅  All data loaded into Cassandra!")

    finally:
        cluster.shutdown()


if __name__ == "__main__":
    main()