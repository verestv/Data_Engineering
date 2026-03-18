# 02_load.py
# Loads all clean CSVs into adtech_db using LOAD DATA LOCAL INFILE

import mysql.connector
import os

DB_CONFIG = {
    "host":               "localhost",
    "port":               3306,
    "user":               "ivan",
    "password":           "StrongPass123!",
    "database":           "advert_db",
    "allow_local_infile": True
}

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))


def get_path(filename: str) -> str:
    return os.path.join(SCRIPT_DIR, filename)


def load(cursor, csv_file: str, table: str, columns: str, set_clause: str = ""):
    path = get_path(csv_file)
    query = f"""
        LOAD DATA LOCAL INFILE '{path}'
        INTO TABLE {table}
        FIELDS TERMINATED BY ','
        LINES TERMINATED BY '\\n'
        IGNORE 1 LINES
        ({columns})
        {set_clause}
    """
    cursor.execute(query)
    print(f"  {table:<20} {cursor.rowcount:>10,} rows")


if __name__ == "__main__":

    conn   = mysql.connector.connect(**DB_CONFIG)
    cursor = conn.cursor()
    print(f"Connected to {DB_CONFIG['database']}.\n")

    # Disable FK checks so load order doesn't matter
    # Re-enabled at the end
    cursor.execute("SET FOREIGN_KEY_CHECKS = 0")
    cursor.execute("SET UNIQUE_CHECKS = 0")      # speeds up bulk load
    cursor.execute("SET AUTOCOMMIT = 0")         # speeds up bulk load

    print("Loading ...")

    load(cursor, "clean_advertisers.csv", "advertisers",
         "advertiser_id, name")

    load(cursor, "clean_ad_slots.csv", "ad_slots",
         "ad_slot_id, size")

    load(cursor, "clean_users.csv", "users",
         "user_id, age, gender, location, signup_date")

    load(cursor, "clean_user_interests.csv", "user_interests",
         "user_id, interest")

    load(cursor, "clean_campaigns.csv", "campaigns",
         """campaign_id, advertiser_id, campaign_name,
            campaign_start_date, campaign_end_date,
            campaign_targeting_criteria, campaign_targeting_interest,
            campaign_targeting_country, budget, remaining_budget""")

    # impression_timestamp has T in the middle: 2024-10-31T06:56:39
    # MySQL needs: 2024-10-31 06:56:39
    # Read into @ts variable then convert
    load(cursor, "clean_impressions.csv", "impressions",
         "event_id, campaign_id, ad_slot_id, user_id, device, location, @ts, bid_amount, ad_cost",
         "SET impression_timestamp = STR_TO_DATE(@ts, '%Y-%m-%dT%H:%i:%s')")

    # same timestamp fix for clicks
    load(cursor, "clean_clicks.csv", "clicks",
         "click_id, event_id, @cts, ad_revenue",
         "SET click_timestamp = STR_TO_DATE(@cts, '%Y-%m-%dT%H:%i:%s')")

    # Commit and re-enable checks
    conn.commit()
    cursor.execute("SET FOREIGN_KEY_CHECKS = 1")
    cursor.execute("SET UNIQUE_CHECKS = 1")
    cursor.execute("SET AUTOCOMMIT = 1")
    conn.commit()

    # Verify
    print("\nRow counts:")
    for table in ["advertisers", "ad_slots", "users", "user_interests",
                  "campaigns", "impressions", "clicks"]:
        cursor.execute(f"SELECT COUNT(*) FROM {table}")
        print(f"  {table:<20} {cursor.fetchone()[0]:>10,}")

    cursor.close()
    conn.close()
    print("\nDone.")
