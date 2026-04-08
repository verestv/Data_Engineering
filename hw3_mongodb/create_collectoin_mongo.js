db.createCollection("user_engagements", {
  validator: {
    $jsonSchema: {
      bsonType: "object",
      required: ["_id", "age", "gender", "country", "signup_date", "interests", "impressions"],
      properties: {
        _id: {
          description: "user_id from MySQL — reused as primary key"
        },
        age: {
          bsonType: "int",
          minimum: 1,
          maximum: 150,
          description: "User age"
        },
        gender: {
          bsonType: "string",
          description: "User gender"
        },
        country: {
          bsonType: "string",
          description: "Denormalized country name"
        },
        signup_date: {
          bsonType: "date",
          description: "Registration date"
        },
        interests: {
          bsonType: "array",
          items: { bsonType: "string" },
          description: "User interests — replaces MySQL bridge table"
        },
        impressions: {
          bsonType: "array",
          description: "All ad impressions for this user",
          items: {
            bsonType: "object",
            required: ["impression_id", "campaign_id", "campaign_name", "advertiser_name", "timestamp"],
            properties: {
              impression_id:   { bsonType: "string" },
              campaign_id:     { bsonType: "int" },
              campaign_name:   { bsonType: "string" },
              advertiser_name: { bsonType: "string" },
              ad_slot_size:    { bsonType: "string" },
              device:          { bsonType: "string" },
              country_served:  { bsonType: "string" },
              timestamp:       { bsonType: "date" },
              bid_amount:      { bsonType: "double" },
              ad_cost:         { bsonType: "double" },
              clicks: {
                bsonType: "array",
                description: "Click events (empty array if no click)",
                items: {
                  bsonType: "object",
                  properties: {
                    click_id:        { bsonType: "string" },
                    click_timestamp: { bsonType: "date" },
                    ad_revenue:      { bsonType: "double" }
                  }
                }
              }
            }
          }
        }
      }
    }
  },
  validationLevel: "moderate",
  validationAction: "warn"
});