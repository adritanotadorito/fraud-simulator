"""
import_creditcard_dataset.py

Downloads the ULB Credit Card Fraud Detection dataset (2000-row sample)
and imports it into MongoDB as real transactions in the fraud_shield_db
transactions collection.

Source: https://github.com/nsethi31/Kaggle-Data-Credit-Card-Fraud-Detection
Dataset: European cardholders, Sept 2013 (anonymized PCA features V1-V28).
"""

import asyncio
import sys
import os
import uuid
import random
import pandas as pd
from datetime import datetime, timezone, timedelta
from motor.motor_asyncio import AsyncIOMotorClient

# ── Config ────────────────────────────────────────────────────────────────────
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "backend"))

MONGO_URI = os.getenv("MONGO_URI", "mongodb://localhost:27017")
DB_NAME   = "fraud_shield_ai"   # Must match backend config.py MONGO_DB_NAME
CSV_PATH  = os.path.join(os.path.dirname(__file__), "backend", "data", "creditcard_sample.csv")

# Merchant pool that feels realistic for card transactions
MERCHANTS = [
    ("Amazon",        "merch_amz_001"),
    ("Flipkart",      "merch_fk_002"),
    ("BigBasket",     "merch_bb_003"),
    ("Swiggy",        "merch_sw_004"),
    ("PhonePe",       "merch_pp_005"),
    ("IRCTC",         "merch_irctc_006"),
    ("Nykaa",         "merch_ny_007"),
    ("Myntra",        "merch_mn_008"),
    ("BookMyShow",    "merch_bms_009"),
    ("Ola",           "merch_ola_010"),
    ("MakeMyTrip",    "merch_mmt_011"),
    ("PayTM Mall",    "merch_ptm_012"),
]

CITIES_GEO = [
    ("Mumbai",    "IN",  19.0760,  72.8777),
    ("Delhi",     "IN",  28.6139,  77.2090),
    ("Bengaluru", "IN",  12.9716,  77.5946),
    ("Chennai",   "IN",  13.0827,  80.2707),
    ("Hyderabad", "IN",  17.3850,  78.4867),
    ("Kolkata",   "IN",  22.5726,  88.3639),
    ("Pune",      "IN",  18.5204,  73.8567),
    ("Ahmedabad", "IN",  23.0225,  72.5714),
]

IPS = [
    "103.211.52.12", "49.206.1.1", "117.218.60.100",
    "182.73.40.2",   "59.95.56.6", "136.232.3.14",
    "27.7.100.5",    "1.186.10.40",
]


def row_to_txn(row, idx: int) -> dict:
    """Map a ULB creditcard.csv row to the MongoDB transaction document."""
    amount    = float(row["Amount"])
    is_fraud  = int(row["Class"]) == 1

    # Derive a realistic timestamp from the 'Time' column (seconds since first txn)
    base_dt = datetime(2024, 9, 1, 0, 0, 0, tzinfo=timezone.utc)
    ts = base_dt + timedelta(seconds=float(row["Time"]))

    merchant_name, merchant_id = random.choice(MERCHANTS)
    city, country, lat, lon = random.choice(CITIES_GEO)
    ip = random.choice(IPS)

    # Build a risk hint from V1-V28 PCA values (high magnitude = suspicious)
    v_magnitudes = [abs(float(row.get(f"V{i}", 0))) for i in range(1, 15)]
    avg_mag = sum(v_magnitudes) / len(v_magnitudes)

    user_idx = (idx % 50) + 1   # map to existing 50 digital-twin users

    return {
        "txn_id":       f"txn_cc_{idx:05d}",
        "account_id":   f"acc_{user_idx:03d}",
        "user_id":      f"usr_{user_idx:03d}",
        "amount":       round(amount, 2),
        "currency":     "USD",
        "merchant_id":  merchant_id,
        "merchant_name": merchant_name,
        "device_id":    f"dev_cc_{random.randint(1, 128):03d}",
        "session_id":   f"sess_cc_{uuid.uuid4().hex[:8]}",
        "geo": {
            "ip":        ip,
            "country":   country,
            "city":      city,
            "latitude":  lat + random.uniform(-0.01, 0.01),
            "longitude": lon + random.uniform(-0.01, 0.01),
        },
        "timestamp":    ts.isoformat(),
        "type":         "purchase",
        "is_fraud":     is_fraud,
        "is_real":      True,
        "is_simulated": False,
        "source":       "creditcard_ulb_dataset",
        # Store top PCA signals for risk engine reference
        "pca_features": {f"V{i}": float(row.get(f"V{i}", 0)) for i in range(1, 8)},
        "pca_magnitude": round(avg_mag, 4),
    }


async def main():
    print("=" * 60)
    print("Fraud Shield AI — ULB Credit Card Dataset Import")
    print("=" * 60)

    if not os.path.exists(CSV_PATH):
        print(f"ERROR: Dataset not found at {CSV_PATH}")
        return

    df = pd.read_csv(CSV_PATH)
    print(f"Loaded {len(df)} rows from creditcard_sample.csv")
    print(f"  Fraud transactions : {int(df['Class'].sum())}")
    print(f"  Legitimate         : {len(df) - int(df['Class'].sum())}")

    client = AsyncIOMotorClient(MONGO_URI)
    db = client[DB_NAME]
    collection = db["transactions"]

    # Remove any previous creditcard import to avoid duplicates
    del_result = await collection.delete_many({"source": "creditcard_ulb_dataset"})
    if del_result.deleted_count:
        print(f"Removed {del_result.deleted_count} previous import records.")

    docs = [row_to_txn(row, idx) for idx, row in df.iterrows()]

    # Batch insert in chunks of 500
    BATCH = 500
    total_inserted = 0
    for i in range(0, len(docs), BATCH):
        batch = docs[i:i + BATCH]
        result = await collection.insert_many(batch)
        total_inserted += len(result.inserted_ids)
        print(f"  Inserted batch {i // BATCH + 1}: {len(result.inserted_ids)} records")

    print(f"\n✅ Done! {total_inserted} real transactions imported into MongoDB.")
    print(f"   View them at: http://localhost:5173/real-data")
    client.close()


if __name__ == "__main__":
    asyncio.run(main())
