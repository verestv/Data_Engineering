import pandas as pd


# ─────────────────────────────────────────────────
# Helper: generic lookup/dimension builder
# ─────────────────────────────────────────────────
def build_lookup(df: pd.DataFrame, col: str, id_col: str, name_col: str):
    """
    Creates a simple dimension table from one string column.
    Returns (DataFrame, name->id dict).
    """
    dim = (
        df[[col]]
        .rename(columns={col: name_col})
        .drop_duplicates()
        .sort_values(name_col)
        .reset_index(drop=True)
    )
    dim[id_col] = dim.index + 1
    dim = dim[[id_col, name_col]]
    return dim, dict(zip(dim[name_col], dim[id_col]))


# ─────────────────────────────────────────────────
# USERS SIDE
# ─────────────────────────────────────────────────
def build_countries(users: pd.DataFrame):
    dim, mapping = build_lookup(users, "location", "country_id", "country_name")
    dim.to_csv("countries.csv", index=False)
    print(f"countries.csv — {len(dim):>8,} rows")
    return dim, mapping


def build_interests(users: pd.DataFrame):
    exploded = (
        users.assign(interests=users["interests"].astype(str).str.split(","))
        .explode("interests")
    )
    exploded["interests"] = exploded["interests"].str.strip()

    dim, mapping = build_lookup(exploded, "interests", "interest_id", "interest_name")
    dim.to_csv("interests.csv", index=False)
    print(f"interests.csv — {len(dim):>8,} rows")
    return dim, exploded, mapping


def build_users_fact(users: pd.DataFrame, country_map: dict):
    users = users.copy()
    users["country_id"] = users["location"].map(country_map)

    fact = users[["user_id", "age", "gender", "country_id", "signup_date"]]
    fact.to_csv("users_fact.csv", index=False)
    print(f"users_fact.csv — {len(fact):>8,} rows")


def build_user_interests(exploded: pd.DataFrame, interest_map: dict):
    ui = (
        exploded[["user_id", "interests"]]
        .rename(columns={"interests": "interest_name"})
        .assign(interest_id=lambda df: df["interest_name"].map(interest_map))
        [["user_id", "interest_id"]]
        .drop_duplicates()
    )
    ui.to_csv("user_interests.csv", index=False)
    print(f"user_interests.csv — {len(ui):>8,} rows")


# ─────────────────────────────────────────────────
# ADTECH SIDE
# ─────────────────────────────────────────────────
def extend_lookup(existing_dim: pd.DataFrame, new_values, id_col: str, name_col: str):
    """
    Append values not yet in the dimension table and return updated mapping.
    """
    known = set(existing_dim[name_col])
    missing = sorted(set(new_values) - known)

    if missing:
        start = existing_dim[id_col].max() + 1
        extra = pd.DataFrame({
            name_col: missing,
            id_col: range(start, start + len(missing))
        })[[id_col, name_col]]

        existing_dim = pd.concat([existing_dim, extra], ignore_index=True)
        print(f" + {len(missing)} new {name_col} values added")

    return existing_dim, dict(zip(existing_dim[name_col], existing_dim[id_col]))


def build_advertisers(ad: pd.DataFrame):
    dim, mapping = build_lookup(ad, "advertiser_name", "advertiser_id", "advertiser_name")
    dim.to_csv("advertisers.csv", index=False)
    print(f"advertisers.csv — {len(dim):>8,} rows")
    return dim, mapping


def build_campaigns(ad: pd.DataFrame, adv_map: dict):
    """
    remaining_budget is intentionally excluded — it is a derived field.
    Compute with: budget - SUM(impressions.ad_cost)
    """
    camps = (
        ad[[
            "advertiser_name",
            "campaign_name",
            "campaign_start_date",
            "campaign_end_date",
            "budget"
        ]]
        .drop_duplicates()
        .reset_index(drop=True)
    )

    camps["advertiser_id"] = camps["advertiser_name"].map(adv_map)
    camps["campaign_id"] = camps.index + 1

    out = camps[[
        "campaign_id",
        "advertiser_id",
        "campaign_name",
        "campaign_start_date",
        "campaign_end_date",
        "budget"
    ]]
    out.to_csv("campaigns.csv", index=False)
    print(f"campaigns.csv — {len(out):>8,} rows")

    key = (
        camps["advertiser_id"].astype(str) + "|"
        + camps["campaign_name"] + "|"
        + camps["campaign_start_date"].astype(str) + "|"
        + camps["campaign_end_date"].astype(str)
    )

    return dict(zip(key, camps["campaign_id"]))


def build_campaign_targeting(
    ad: pd.DataFrame,
    campaign_map: dict,
    adv_map: dict,
    interest_map: dict,
    country_map: dict
):
    """
    targeting_criteria (e.g. '25-45') is parsed into age_min / age_max.
    This makes range queries possible and allows CHECK constraints.
    """
    ad = ad.copy()

    ad["camp_key"] = (
        ad["advertiser_name"].map(adv_map).astype(str) + "|"
        + ad["campaign_name"] + "|"
        + ad["campaign_start_date"].astype(str) + "|"
        + ad["campaign_end_date"].astype(str)
    )
    ad["campaign_id"] = ad["camp_key"].map(campaign_map)

    parsed = ad["targeting_criteria"].astype(str).str.extract(r"(\d+)[-–](\d+)")
    ad["age_min"] = pd.to_numeric(parsed[0], errors="coerce").astype("Int64")
    ad["age_max"] = pd.to_numeric(parsed[1], errors="coerce").astype("Int64")

    ad["target_interest_id"] = ad["target_interest"].map(interest_map)
    ad["target_country_id"] = ad["target_country"].map(country_map)

    ct = (
        ad[[
            "campaign_id",
            "age_min",
            "age_max",
            "target_interest_id",
            "target_country_id"
        ]]
        .drop_duplicates(subset=["campaign_id"])
        .reset_index(drop=True)
    )

    ct.to_csv("campaign_targeting.csv", index=False)
    print(f"campaign_targeting.csv — {len(ct):>8,} rows")

    return ad


def build_impressions_and_clicks(ad: pd.DataFrame):
    """
    Split the original ad_events into two tables:
    impressions — one row per ad served
    clicks — one row per click (only rows where was_clicked == True)

    was_clicked column is NOT written to either table — it is derived from
    whether a row exists in the clicks table for a given impression_id.

    ad_revenue belongs to clicks because revenue only occurs on a click.
    remaining_budget is NOT written — it is a derived field.
    """
    impressions = ad[[
        "event_id",
        "campaign_id",
        "user_id",
        "ad_slot_size",
        "device",
        "served_country_id",
        "event_timestamp",
        "bid_amount",
        "ad_cost",
    ]].rename(columns={"event_id": "impression_id"})

    impressions.to_csv("impressions.csv", index=False)
    print(f"impressions.csv — {len(impressions):>8,} rows")

    clicked = ad[
        ad["was_clicked"].astype(str).str.lower().isin(["true", "1"])
    ].copy()

    clicked["click_id"] = clicked["event_id"].astype(str) + "-click"

    clicks = clicked[[
        "click_id",
        "event_id",
        "click_timestamp",
        "ad_revenue",
    ]].rename(columns={"event_id": "impression_id"})

    clicks.to_csv("clicks.csv", index=False)
    print(f"clicks.csv — {len(clicks):>8,} rows")


# ─────────────────────────────────────────────────
# MAIN
# ─────────────────────────────────────────────────
def main():
    print("\n=== Reading source files ===")
    users = pd.read_csv("users.csv", engine="pyarrow")
    ad = pd.read_csv("ad_events_header_updated.csv", engine="pyarrow")

    print("\n=== Building dimensions from users.csv ===")
    countries_dim, country_map = build_countries(users)
    interests_dim, exploded, int_map = build_interests(users)
    build_users_fact(users, country_map)
    build_user_interests(exploded, int_map)

    print("\n=== Extending dimensions with adtech data ===")
    countries_dim, country_map = extend_lookup(
        countries_dim,
        list(ad["served_country"]) + list(ad["target_country"]),
        "country_id",
        "country_name",
    )
    countries_dim.to_csv("countries.csv", index=False)

    interests_dim, int_map = extend_lookup(
        interests_dim,
        ad["target_interest"].tolist(),
        "interest_id",
        "interest_name",
    )
    interests_dim.to_csv("interests.csv", index=False)

    ad["served_country_id"] = ad["served_country"].map(country_map)

    print("\n=== Building adtech tables ===")
    _, adv_map = build_advertisers(ad)
    campaign_map = build_campaigns(ad, adv_map)
    ad = build_campaign_targeting(ad, campaign_map, adv_map, int_map, country_map)
    build_impressions_and_clicks(ad)

    print("\n=== All CSVs generated. Ready for LOAD DATA INFILE. ===")


if __name__ == "__main__":
    main()
