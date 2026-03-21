import csv

COLUMN_MAPPING = {
    "EventID": "event_id",
    "AdvertiserName": "advertiser_name",
    "CampaignName": "campaign_name",
    "CampaignStartDate": "campaign_start_date",
    "CampaignEndDate": "campaign_end_date",
    "CampaignTargetingCriteria": "targeting_criteria",
    "CampaignTargetingInterest": "target_interest",
    "CampaignTargetingCountry": "target_country",
    "AdSlotSize": "ad_slot_size",
    "UserID": "user_id",
    "Device": "device",
    "Location": "served_country",
    "Timestamp": "event_timestamp",
    "BidAmount": "bid_amount",
    "AdCost": "ad_cost",
    "WasClicked": "was_clicked",
    "ClickTimestamp": "click_timestamp",
    "AdRevenue": "ad_revenue",
    "Budget": "budget",
    "RemainingBudget": "remaining_budget",
}

FILE = "ad_events_header_updated.csv"

with open(FILE, "r+", newline="") as f:
    first_line = f.readline()
    rest_offset = f.tell()  # remember where data starts
    
    # Rename headers
    old_headers = first_line.rstrip("\n").split(",")
    new_headers = [COLUMN_MAPPING.get(h, h) for h in old_headers]
    new_first_line = ",".join(new_headers) + "\n"
    
    # Go back to start and overwrite only the first line
    f.seek(0)
    f.write(new_first_line)

print("Done! Header updated in place.")