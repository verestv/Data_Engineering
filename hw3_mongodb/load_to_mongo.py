"""
load_to_mongo.py - CSV to MongoDB ETL for user_engagements collection.

Prerequisites:
  - Run mongo_schema.js first to create collection + indexes
  - CSV files from build_csvs.py available

Strategy (memory-efficient, streaming):
  1. Load small lookup CSVs into memory
  2. Clear existing documents (idempotent re-runs)
  3. Insert all users as base documents (empty impressions array)
  4. Stream impressions.csv in chunks, denormalize, $push to MongoDB
     (never holds more than CHUNK_SIZE impressions in RAM)
"""

import pandas as pd
from pymongo import MongoClient, UpdateOne
from datetime import datetime
from dotenv import load_dotenv
import time
import os
import sys

# Load .env
load_dotenv()
load_dotenv(dotenv_path=os.path.join("..", ".env"))

# ──────────────────────────────────────────────
# CONFIG
# ──────────────────────────────────────────────
CSV_DIR = os.environ.get("CSV_DIR", ".")

_mongo_user = os.environ.get("MONGO_INITDB_ROOT_USERNAME",) # value from .env file
_mongo_pass = os.environ.get("MONGO_INITDB_ROOT_PASSWORD",)
MONGO_URI = os.environ.get(
    "MONGO_URI",
    f"mongodb://{_mongo_user}:{_mongo_pass}@localhost:27017/"
)
MONGO_DB = os.environ.get("MONGO_DB", "adtech_db")
COLLECTION = "user_engagements"

CHUNK_SIZE = 100_000


# ──────────────────────────────────────────────
# HELPERS
# ──────────────────────────────────────────────
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


def load_csv(name, **kwargs):
    path = os.path.join(CSV_DIR, name)
    if not os.path.exists(path):
        print(f"  ✗ {name} — FILE NOT FOUND at {path}")
        sys.exit(1)
    print(f"  Loading {name}...", end=" ", flush=True)
    t = time.time()
    df = pd.read_csv(path, engine="pyarrow", **kwargs)
    elapsed = time.time() - t
    print(f"{len(df):,} rows ({elapsed:.1f}s)")
    return df


# ──────────────────────────────────────────────
# MAIN
# ──────────────────────────────────────────────
def main():
    t_start = time.time()

    # ─── 1. Connect ───
    print("\n═══ Connecting to MongoDB ═══")
    client = MongoClient(MONGO_URI)
    db = client[MONGO_DB]
    col = db[COLLECTION]

    # Verify collection exists (should be created by mongo_schema.js)
    if COLLECTION not in db.list_collection_names():
        print(f"  ✗ Collection '{COLLECTION}' not found!")
        print(f"    Run mongo_schema.js first:")
        print(f"    docker exec -it adtech_mongo mongosh -u root -p mongopass --authenticationDatabase admin < mongo_schema.js")
        sys.exit(1)

    # Clear existing documents for clean re-run
    existing = col.count_documents({})
    if existing > 0:
        print(f"  Clearing {existing:,} existing documents...")
        col.delete_many({})
    print("  ✓ Connected")

    # ─── 2. Load lookup CSVs ───
    print("\n═══ Loading lookup CSVs ═══")
    countries = load_csv("countries.csv")
    interests = load_csv("interests.csv")
    advertisers = load_csv("advertisers.csv")
    campaigns = load_csv("campaigns.csv")
    users = load_csv("users_fact.csv")
    user_interests = load_csv("user_interests.csv")
    clicks_df = load_csv("clicks.csv")

    # ─── 3. Build lookups ───
    print("\n═══ Building lookup dictionaries ═══")

    country_map = dict(zip(countries["country_id"], countries["country_name"]))

    camp_merged = campaigns.merge(advertisers, on="advertiser_id", how="left")
    campaign_name_map = dict(zip(camp_merged["campaign_id"], camp_merged["campaign_name"]))
    campaign_adv_map = dict(zip(camp_merged["campaign_id"], camp_merged["advertiser_name"]))

    ui_merged = user_interests.merge(interests, on="interest_id", how="left")
    user_interest_names = (
        ui_merged.groupby("user_id")["interest_name"]
        .apply(list)
        .to_dict()
    )

    print(f"  ✓ {len(country_map):,} countries, {len(campaign_name_map):,} campaigns")

    # ─── 4. Build clicks index ───
    print("\n═══ Building clicks index ═══")
    t_clicks = time.time()

    clicks_df["click_timestamp"] = pd.to_datetime(clicks_df["click_timestamp"], errors="coerce")
    clicks_records = clicks_df.to_dict("records")
    clicks_by_imp = {}
    for row in clicks_records:
        imp_id = str(row["impression_id"])
        click_doc = {
            "click_id": str(row["click_id"]),
            "click_timestamp": row["click_timestamp"].to_pydatetime()
                if pd.notna(row["click_timestamp"]) else None,
            "ad_revenue": float(row["ad_revenue"]) if pd.notna(row["ad_revenue"]) else 0.0,
        }
        clicks_by_imp.setdefault(imp_id, []).append(click_doc)

    del clicks_df, clicks_records
    print(f"  ✓ {len(clicks_by_imp):,} impressions have clicks ({fmt_time(time.time() - t_clicks)})")

    # ─── 5. Insert base user documents ───
    print("\n═══ Inserting base user documents ═══")
    t_users = time.time()

    n_users = len(users)
    BATCH = 5000
    inserted = 0

    for start in range(0, n_users, BATCH):
        batch_df = users.iloc[start:start + BATCH]
        docs = []
        for _, u in batch_df.iterrows():
            uid = int(u["user_id"])
            docs.append({
                "_id": uid,
                "age": int(u["age"]),
                "gender": str(u["gender"]),
                "country": str(country_map.get(int(u["country_id"]), "Unknown")),
                "signup_date": datetime.strptime(str(u["signup_date"]), "%Y-%m-%d"),
                "interests": user_interest_names.get(uid, []),
                "impressions": [],
            })
        try:
            col.insert_many(docs, ordered=False)
            inserted += len(docs)
        except Exception as e:
            # ordered=False means valid docs still inserted; count what we sent
            inserted += len(docs)
            err_msg = str(e)[:150]
            print(f"\n  ⚠ Batch warning: {err_msg}")
        progress_bar(inserted, n_users, prefix="Users: ")

    del users, user_interests, ui_merged, user_interest_names
    actual_count = col.count_documents({})
    print(f"\n  ✓ {actual_count:,} users in MongoDB ({fmt_time(time.time() - t_users)})")

    # --- 6. Stream impressions, $push to MongoDB ---
    print(f"\n═══ Processing impressions.csv in {CHUNK_SIZE:,}-row chunks ═══")

    imp_path = os.path.join(CSV_DIR, "impressions.csv")

    print("  Counting rows...", end=" ", flush=True)
    with open(imp_path, "r") as f:
        total_rows = sum(1 for _ in f) - 1
    total_chunks = (total_rows + CHUNK_SIZE - 1) // CHUNK_SIZE
    print(f"{total_rows:,} rows ({total_chunks} chunks)")

    total_imp = 0
    chunk_num = 0
    chunk_times = []
    skipped_users = set()
    total_pushed = 0

    valid_users = set(doc["_id"] for doc in col.find({}, {"_id": 1}))
    print(f"  ✓ {len(valid_users):,} valid users loaded")

    for chunk in pd.read_csv(imp_path, chunksize=CHUNK_SIZE, engine="c"):
        chunk_num += 1
        total_imp += len(chunk)
        t_chunk = time.time()

        # Extract numpy arrays
        imp_ids = chunk["impression_id"].astype(str).values
        camp_ids = chunk["campaign_id"].values
        user_ids = chunk["user_id"].values
        ad_slots = chunk["ad_slot_size"].astype(str).values
        devices = chunk["device"].astype(str).values
        country_ids = chunk["served_country_id"].values
        timestamps = pd.to_datetime(chunk["event_timestamp"], errors="coerce").values
        bids = chunk["bid_amount"].values
        costs = chunk["ad_cost"].values

        # Group by user
        user_impressions = {}

        for i in range(len(chunk)):
            uid = int(user_ids[i])
            if uid not in valid_users:
                skipped_users.add(uid)
                continue

            imp_id = str(imp_ids[i])
            ts = timestamps[i]
            ts_py = pd.Timestamp(ts).to_pydatetime() if not pd.isna(ts) else None

            impression_doc = {
                "impression_id": imp_id,
                "campaign_id": int(camp_ids[i]),
                "campaign_name": campaign_name_map.get(int(camp_ids[i]), "Unknown"),
                "advertiser_name": campaign_adv_map.get(int(camp_ids[i]), "Unknown"),
                "ad_slot_size": str(ad_slots[i]),
                "device": str(devices[i]),
                "country_served": country_map.get(int(country_ids[i]), "Unknown"),
                "timestamp": ts_py,
                "bid_amount": float(bids[i]),
                "ad_cost": float(costs[i]),
                "clicks": clicks_by_imp.get(imp_id, []),
            }
            user_impressions.setdefault(uid, []).append(impression_doc)

        # Batch $push
        if user_impressions:
            ops = [
                UpdateOne(
                    {"_id": uid},
                    {"$push": {"impressions": {"$each": imps}}}
                )
                for uid, imps in user_impressions.items()
            ]
            OP_BATCH = 1000
            for j in range(0, len(ops), OP_BATCH):
                try:
                    col.bulk_write(ops[j:j + OP_BATCH], ordered=False)
                except Exception as e:
                    print(f"\n  ⚠ Chunk {chunk_num} write error: {str(e)[:150]}")
            total_pushed += sum(len(v) for v in user_impressions.values())

        del user_impressions

        elapsed = time.time() - t_chunk
        chunk_times.append(elapsed)
        avg_chunk = sum(chunk_times) / len(chunk_times)
        remaining = (total_chunks - chunk_num) * avg_chunk
        eta_str = fmt_time(remaining) if remaining > 0 else "done"
        progress_bar(
            chunk_num, total_chunks,
            prefix="Imps: ",
            extra=f"{elapsed:.1f}s/chunk  ETA: {eta_str}   "
        )

    print(f"\n  ✓ Impressions loaded: {total_pushed:,}")
    if skipped_users:
        print(f"  ⚠ {len(skipped_users)} unknown user_ids skipped")

    # ─── 7. Summary ───
    t_end = time.time()
    final_count = col.count_documents({})

    print(f"\n═══════════════════════════════")
    print(f"  ✓ DONE")
    print(f"  Documents: {final_count:,}")
    print(f"  Impressions: {total_pushed:,}")
    print(f"  Total time: {fmt_time(t_end - t_start)}")
    print(f"═══════════════════════════════")

    # Sanity check
    sample = col.find_one({"impressions.0": {"$exists": True}})
    if sample:
        n_imps = len(sample.get("impressions", []))
        n_clicks = sum(1 for imp in sample["impressions"] if imp.get("clicks"))
        print(f"\n  Sample user _id={sample['_id']}:")
        print(f"    Age={sample['age']}, Gender={sample['gender']}, Country={sample['country']}")
        print(f"    Interests: {sample['interests']}")
        print(f"    Impressions: {n_imps:,}, with clicks: {n_clicks:,}")

    client.close()


if __name__ == "__main__":
    main()