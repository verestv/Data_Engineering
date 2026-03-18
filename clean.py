# 02_clean.py
# Handles large CSV files by processing row by row (no full load into memory)
# Uses pandas for efficient CSV writing and functions to keep code clean

import csv
import uuid
import os
import pandas as pd


# ----------------------------------------------------------
# HELPER FUNCTIONS
# ----------------------------------------------------------

def strip_row(row: dict) -> dict:
    """Strip whitespace from all values in a CSV row."""
    return {k: v.strip() for k, v in row.items()}


def open_writer(filename: str, fieldnames: list):
    """Open a CSV file for writing, return (file_handle, DictWriter)."""
    f = open(filename, "w", newline="", encoding="utf-8")
    writer = csv.DictWriter(f, fieldnames=fieldnames)
    writer.writeheader()
    return f, writer


# ----------------------------------------------------------
# CLEAN USERS
# ----------------------------------------------------------

def clean_users(input_file: str):
    """
    Reads users.csv row by row.
    Splits Interests column into separate rows → clean_user_interests.csv
    Saves clean user rows → clean_users.csv
    """
    print(f"Cleaning {input_file} ...")

    user_count     = 0
    interest_count = 0

    f_users,     w_users     = open_writer("clean_users.csv",
                                           ["UserID", "Age", "Gender", "Location", "SignupDate"])
    f_interests, w_interests = open_writer("clean_user_interests.csv",
                                           ["UserID", "Interest"])

    with open(input_file, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            row = strip_row(row)

            w_users.writerow({
                "UserID":     row["UserID"],
                "Age":        row["Age"],
                "Gender":     row["Gender"],
                "Location":   row["Location"],
                "SignupDate": row["SignupDate"]
            })
            user_count += 1

            # Split "Gaming,Sports,Health" → 3 rows
            for interest in row["Interests"].split(","):
                interest = interest.strip()
                if interest:
                    w_interests.writerow({"UserID": row["UserID"], "Interest": interest})
                    interest_count += 1

    f_users.close()
    f_interests.close()

    print(f"  Users:     {user_count}")
    print(f"  Interests: {interest_count}")


# ----------------------------------------------------------
# CLEAN AD EVENTS  (large file — row by row)
# ----------------------------------------------------------

def clean_ad_events(input_file: str):
    print(f"\nCleaning {input_file} ...")

    advertisers: dict = {}
    campaigns:   dict = {}
    slots:       dict = {}

    adv_counter  = 1
    camp_counter = 1
    slot_counter = 1

    impression_count = 0
    click_count      = 0

    f_imp, w_imp = open_writer("clean_impressions.csv", [
        "EventID", "campaign_id", "ad_slot_id", "UserID",
        "Device", "Location", "Timestamp", "BidAmount", "AdCost"
    ])
    f_clk, w_clk = open_writer("clean_clicks.csv", [
        "click_id", "EventID", "ClickTimestamp", "AdRevenue"
    ])

    with open(input_file, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)

        for row in reader:
            row = strip_row(row)

            adv_name  = row["AdvertiserName"]
            camp_name = row["CampaignName"]
            slot_size = row["AdSlotSize"]

            # Advertiser
            if adv_name not in advertisers:
                advertisers[adv_name] = adv_counter
                adv_counter += 1
            adv_id = advertisers[adv_name]

            # Campaign
            if camp_name not in campaigns:
                campaigns[camp_name] = {
                    "campaign_id":               camp_counter,   # <-- fixed
                    "advertiser_id":             adv_id,
                    "CampaignName":              camp_name,
                    "CampaignStartDate":         row["CampaignStartDate"],
                    "CampaignEndDate":           row["CampaignEndDate"],
                    "CampaignTargetingCriteria": row["CampaignTargetingCriteria"],
                    "CampaignTargetingInterest": row["CampaignTargetingInterest"],
                    "CampaignTargetingCountry":  row["CampaignTargetingCountry"],
                    "Budget":                    row["Budget"],
                    "RemainingBudget":           row["RemainingBudget"]
                }
                camp_counter += 1                               # <-- fixed
            camp_id = campaigns[camp_name]["campaign_id"]

            # Slot
            if slot_size not in slots:
                slots[slot_size] = slot_counter
                slot_counter += 1
            slot_id = slots[slot_size]

            # Write impression
            w_imp.writerow({
                "EventID":     row["EventID"],
                "campaign_id": camp_id,
                "ad_slot_id":  slot_id,
                "UserID":      row["UserID"],
                "Device":      row["Device"],
                "Location":    row["Location"],
                "Timestamp":   row["Timestamp"],
                "BidAmount":   row["BidAmount"],
                "AdCost":      row["AdCost"]
            })
            impression_count += 1

            # Write click if clicked
            if row["WasClicked"] == "True":
                w_clk.writerow({
                    "click_id":       str(uuid.uuid4()),
                    "EventID":        row["EventID"],
                    "ClickTimestamp": row["ClickTimestamp"],
                    "AdRevenue":      row["AdRevenue"]
                })
                click_count += 1

            if impression_count % 100_000 == 0:
                print(f"  ... processed {impression_count:,} rows")

    f_imp.close()
    f_clk.close()

    save_lookup_tables(advertisers, campaigns, slots)

    print(f"  Advertisers:  {len(advertisers)}")
    print(f"  Campaigns:    {len(campaigns)}")
    print(f"  Ad slots:     {len(slots)}")
    print(f"  Impressions:  {impression_count:,}")
    print(f"  Clicks:       {click_count:,}")

# ----------------------------------------------------------
# SAVE LOOKUP TABLES (called after processing events)
# ----------------------------------------------------------

def save_lookup_tables(advertisers: dict, campaigns: dict, slots: dict):
    """Write the three small lookup tables to CSV."""

    # Advertisers
    with open("clean_advertisers.csv", "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=["advertiser_id", "name"])
        writer.writeheader()
        for name, aid in advertisers.items():
            writer.writerow({"advertiser_id": aid, "name": name})

    # Campaigns
    camp_fields = [
        "campaign_id", "advertiser_id", "CampaignName",
        "CampaignStartDate", "CampaignEndDate",
        "CampaignTargetingCriteria", "CampaignTargetingInterest",
        "CampaignTargetingCountry", "Budget", "RemainingBudget"
    ]
    with open("clean_campaigns.csv", "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=camp_fields)
        writer.writeheader()
        writer.writerows(campaigns.values())

    # Ad slots
    with open("clean_ad_slots.csv", "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=["ad_slot_id", "size"])
        writer.writeheader()
        for size, sid in slots.items():
            writer.writerow({"ad_slot_id": sid, "size": size})

    print("  Lookup tables saved.")


# ----------------------------------------------------------
# MAIN — run everything
# ----------------------------------------------------------

if __name__ == "__main__":
    # Check files exist before starting
    for fname in ["users.csv", "ad_events_header_updated.csv"]:
        if not os.path.exists(fname):
            print(f"ERROR: {fname} not found in current folder.")
            exit(1)

    clean_users("users.csv")
    clean_ad_events("ad_events_header_updated.csv")

    print("\nDone. Clean files ready:")
    for fname in [
        "clean_users.csv", "clean_user_interests.csv",
        "clean_advertisers.csv", "clean_ad_slots.csv",
        "clean_campaigns.csv", "clean_impressions.csv", "clean_clicks.csv"
    ]:
        size_mb = os.path.getsize(fname) / 1_000_000
        print(f"  {fname:35s} {size_mb:.1f} MB")
