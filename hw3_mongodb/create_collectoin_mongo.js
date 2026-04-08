db.createCollection("user_engagements", {
  validator: {
    $jsonSchema: {
      bsonType: "object",
      required: ["_id", "age", "gender", "country", "signup_date", "interests", "impressions"],
      properties: {
        _id: {
          bsonType: "long",
          description: "user_id from MySQL — reused as primary key"
        },
        age: {
          bsonType: "int",
          minimum: 1,
          maximum: 150,
          description: "User age, must be 1-150"
        },
        gender: {
          bsonType: "string",
          description: "User gender"
        },
        country: {
          bsonType: "string",
          description: "Denormalized country name (not ID)"
        },
        signup_date: {
          bsonType: "date",
          description: "When the user registered"
        },
        interests: {
          bsonType: "array",
          items: { bsonType: "string" },
          description: "List of user interests — replaces MySQL bridge table"
        },
        impressions: {
          bsonType: "array",
          description: "All ad impressions for this user",
          items: {
            bsonType: "object",
            required: ["impression_id", "campaign_id", "campaign_name", "advertiser_name", "timestamp"],
            properties: {
              impression_id: {
                bsonType: "string",
                description: "UUID from impressions table"
              },
              campaign_id: {
                bsonType: "long",
                description: "Campaign FK"
              },
              campaign_name: {
                bsonType: "string",
                description: "Denormalized from campaigns table"
              },
              advertiser_name: {
                bsonType: "string",
                description: "Denormalized from advertisers table"
              },
              ad_slot_size: {
                bsonType: "string",
                description: "Ad dimensions e.g. 300x250"
              },
              device: {
                bsonType: "string",
                description: "mobile / desktop / tablet"
              },
              country_served: {
                bsonType: "string",
                description: "Country where ad was shown"
              },
              timestamp: {
                bsonType: "date",
                description: "When the impression was served"
              },
              bid_amount: {
                bsonType: "double",
                description: "Bid price for this impression"
              },
              ad_cost: {
                bsonType: "double",
                description: "Actual cost charged"
              },
              clicks: {
                bsonType: "array",
                description: "Click events for this impression (empty array if no click)",
                items: {
                  bsonType: "object",
                  properties: {
                    click_id: {
                      bsonType: "string",
                      description: "Click UUID"
                    },
                    click_timestamp: {
                      bsonType: "date",
                      description: "When the click happened"
                    },
                    ad_revenue: {
                      bsonType: "double",
                      description: "Revenue generated from this click"
                    }
                  }
                }
              }
            }
          }
        }
      }
    }
  },
  validationLevel: "strict",
  validationAction: "error"
})