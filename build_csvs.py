import pandas as pd

# =========================
# 1) USERS SIDE
# =========================

print("Reading users.csv ...")
users = pd.read_csv("users.csv", engine="pyarrow")  # user_id, age, gender, location, interests, signup_date

# ---------- DIM: countries ----------
print("Building countries ...")
countries = (
    users[["location"]]
    .rename(columns={"location": "country_name"})
    .drop_duplicates()
    .sort_values("country_name")
    .reset_index(drop=True)
)
countries["country_id"] = countries.index + 1
countries = countries[["country_id", "country_name"]]
countries.to_csv("countries.csv", index=False)
print(f"countries.csv written with {len(countries)} rows")

# Map country_name -> id
country_map = dict(zip(countries["country_name"], countries["country_id"]))

# ---------- DIM: interests ----------
print("Building interests ...")
users["interests"] = users["interests"].astype(str).str.split(",")
exploded = users.explode("interests")
exploded["interests"] = exploded["interests"].str.strip()
exploded = exploded.dropna(subset=["interests"])

interests = (
    exploded[["interests"]]
    .drop_duplicates()
    .rename(columns={"interests": "interest_name"})
    .sort_values("interest_name")
    .reset_index(drop=True)
)
interests["interest_id"] = interests.index + 1
interests = interests[["interest_id", "interest_name"]]
interests.to_csv("interests.csv", index=False)
print(f"interests.csv written with {len(interests)} rows")

# Map interest_name -> id
interest_map = dict(zip(interests["interest_name"], interests["interest_id"]))

# ---------- FACT: users ----------
print("Building users_fact ...")
users["country_id"] = users["location"].map(country_map)
users_fact = users[["user_id", "age", "gender", "country_id", "signup_date"]]
users_fact.to_csv("users_fact.csv", index=False)
print(f"users_fact.csv written with {len(users_fact)} rows")

# ---------- BRIDGE: user_interests ----------
print("Building user_interests ...")
ui = exploded[["user_id", "interests"]].rename(columns={"interests": "interest_name"})
ui["interest_id"] = ui["interest_name"].map(interest_map)
user_interests = ui[["user_id", "interest_id"]].drop_duplicates()
user_interests.to_csv("user_interests.csv", index=False)
print(f"user_interests.csv written with {len(user_interests)} rows")

# =========================
# 2) ADTECH SIDE
# =========================

print("Reading ad_events_header_updated.csv ...")
ad = pd.read_csv("ad_events_header_updated.csv", engine="pyarrow")

# Expected columns in ad:
# event_id, advertiser_name, campaign_name, campaign_start_date, campaign_end_date,
# targeting_criteria, target_interest, target_country, ad_slot_size,
# user_id, device, served_country, event_timestamp, bid_amount, ad_cost,
# was_clicked, click_timestamp, ad_revenue, budget, remaining_budget

# ---------- DIM: advertisers ----------
print("Building advertisers ...")
advertisers = (
    ad[["advertiser_name"]]
    .drop_duplicates()
    .sort_values("advertiser_name")
    .reset_index(drop=True)
)
advertisers["advertiser_id"] = advertisers.index + 1
advertisers = advertisers[["advertiser_id", "advertiser_name"]]
advertisers.to_csv("advertisers.csv", index=False)
print(f"advertisers.csv written with {len(advertisers)} rows")

adv_map = dict(zip(advertisers["advertiser_name"], advertisers["advertiser_id"]))

# ---------- MAP countries & interests on adtech ----------
print("Mapping countries and interests on adtech ...")

# If adtech has country names not present in users.csv, you may want to add them:
# find missing served/target countries and append to countries before mapping
served_missing = sorted(set(ad["served_country"]) - set(countries["country_name"]))
target_missing = sorted(set(ad["target_country"]) - set(countries["country_name"]))
all_missing_countries = sorted(set(served_missing + target_missing))

if all_missing_countries:
    print(f"Found {len(all_missing_countries)} new countries from adtech, appending ...")
    # Start IDs after existing ones
    start_id = countries["country_id"].max() + 1
    new_c = pd.DataFrame({
        "country_name": all_missing_countries,
        "country_id": range(start_id, start_id + len(all_missing_countries))
    })[["country_id", "country_name"]]
    countries = pd.concat([countries, new_c], ignore_index=True)
    countries = countries.sort_values("country_id").reset_index(drop=True)
    countries.to_csv("countries.csv", index=False)  # overwrite with updated
    country_map = dict(zip(countries["country_name"], countries["country_id"]))

# Map country names to IDs
ad["target_country_id"] = ad["target_country"].map(country_map)
ad["served_country_id"] = ad["served_country"].map(country_map)

# Handle missing interests from adtech vs users side
missing_interests = sorted(set(ad["target_interest"]) - set(interests["interest_name"]))
if missing_interests:
    print(f"Found {len(missing_interests)} new interests from adtech, appending ...")
    start_id = interests["interest_id"].max() + 1
    new_i = pd.DataFrame({
        "interest_name": missing_interests,
        "interest_id": range(start_id, start_id + len(missing_interests))
    })[["interest_id", "interest_name"]]
    interests = pd.concat([interests, new_i], ignore_index=True)
    interests = interests.sort_values("interest_id").reset_index(drop=True)
    interests.to_csv("interests.csv", index=False)  # overwrite with updated
    interest_map = dict(zip(interests["interest_name"], interests["interest_id"]))

ad["target_interest_id"] = ad["target_interest"].map(interest_map)

# ---------- DIM/FACT: campaigns ----------
print("Building campaigns ...")
campaigns = (
    ad[
        [
            "advertiser_name",
            "campaign_name",
            "campaign_start_date",
            "campaign_end_date",
            "budget",
            "remaining_budget",
        ]
    ]
    .drop_duplicates()
    .reset_index(drop=True)
)

campaigns["advertiser_id"] = campaigns["advertiser_name"].map(adv_map)
campaigns["campaign_id"] = campaigns.index + 1

campaigns_out = campaigns[
    [
        "campaign_id",
        "advertiser_id",
        "campaign_name",
        "campaign_start_date",
        "campaign_end_date",
        "budget",
        "remaining_budget",
    ]
]
campaigns_out.to_csv("campaigns.csv", index=False)
print(f"campaigns.csv written with {len(campaigns_out)} rows")

# Map full campaign key -> campaign_id
camp_key = (
    campaigns["advertiser_id"].astype(str)
    + "|"
    + campaigns["campaign_name"]
    + "|"
    + campaigns["campaign_start_date"].astype(str)
    + "|"
    + campaigns["campaign_end_date"].astype(str)
)
campaign_map = dict(zip(camp_key, campaigns["campaign_id"]))

# Attach campaign_id to ad rows
ad_key = (
    ad["advertiser_name"].map(adv_map).astype(str)
    + "|"
    + ad["campaign_name"]
    + "|"
    + ad["campaign_start_date"].astype(str)
    + "|"
    + ad["campaign_end_date"].astype(str)
)
ad["campaign_id"] = ad_key.map(campaign_map)

# ---------- campaign_targeting ----------
print("Building campaign_targeting ...")
campaign_targeting = (
    ad[
        [
            "campaign_id",
            "targeting_criteria",
            "target_interest_id",
            "target_country_id",
        ]
    ]
    .drop_duplicates(subset=["campaign_id"])
    .reset_index(drop=True)
)
campaign_targeting.to_csv("campaign_targeting.csv", index=False)
print(f"campaign_targeting.csv written with {len(campaign_targeting)} rows")

# ---------- ad_events ----------
print("Building ad_events ...")
ad_events = ad[
    [
        "event_id",
        "campaign_id",
        "user_id",
        "ad_slot_size",
        "device",
        "served_country_id",
        "event_timestamp",
        "bid_amount",
        "ad_cost",
        "was_clicked",
        "click_timestamp",
        "ad_revenue",
    ]
]
ad_events.to_csv("ad_events.csv", index=False)
print(f"ad_events.csv written with {len(ad_events)} rows")

print("All CSVs generated. You can now LOAD DATA INFILE into MySQL.")
