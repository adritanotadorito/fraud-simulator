"""
transactions.py router — upload, score, list, stream endpoints.

Auth-aware: upload-file, uploaded, my-uploads, score-uploaded require login.
Admins can see any user's uploads; regular users only see their own.
"""

from fastapi import APIRouter, HTTPException, Query, WebSocket, WebSocketDisconnect, UploadFile, File, Depends
from typing import Optional
import logging
import csv
import json
import io
import uuid
import random
from datetime import datetime, timezone

from app.database import find_many, find_one, insert_one, get_database
from app.ws.manager import get_manager
from app.auth.dependencies import get_current_user

# Merchant / city pools for auto-enriching uploaded rows
_MERCHANTS = [
    ("Amazon", "merch_amz_001"), ("Flipkart", "merch_fk_002"),
    ("Swiggy", "merch_sw_003"), ("BigBasket", "merch_bb_004"),
    ("IRCTC", "merch_irctc_005"), ("Ola", "merch_ola_006"),
    ("MakeMyTrip", "merch_mmt_007"), ("Nykaa", "merch_ny_008"),
]
_CITIES = [
    ("Mumbai", "IN", 19.0760, 72.8777),
    ("Delhi", "IN", 28.6139, 77.2090),
    ("Bengaluru", "IN", 12.9716, 77.5946),
    ("Chennai", "IN", 13.0827, 80.2707),
    ("Hyderabad", "IN", 17.3850, 78.4867),
]

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/transactions", tags=["Transactions"])


@router.get("/")
async def list_transactions(
    limit: int = Query(50, ge=1, le=500),
    offset: int = Query(0, ge=0),
    account_id: Optional[str] = None,
    user_id: Optional[str] = None
):
    """List recent transactions."""
    query = {}
    if account_id:
        query["account_id"] = account_id
    if user_id:
        query["user_id"] = user_id
    results = await find_many("transactions", query, limit=limit, sort=[("timestamp", -1)])
    for r in results:
        r.pop("_id", None)
    return results


@router.get("/uploaded")
async def list_uploaded_transactions(
    source: str = Query(..., description="Source tag from upload, e.g. 'upload:filename.csv'"),
    limit: int = Query(10000, ge=1, le=50000),
    current_user: dict = Depends(get_current_user),
):
    """Return all transactions from a specific uploaded file.
    Regular users only see their own uploads; admins can see any source."""
    db = get_database()
    query = {"source": source}
    # Non-admins can only see their own uploads
    if current_user.get("role") != "admin":
        query["uploaded_by"] = current_user["id"]
    cursor = db["transactions"].find(query).limit(limit)
    results = await cursor.to_list(length=limit)
    for doc in results:
        doc.pop("_id", None)
    return results


@router.get("/my-uploads")
async def my_uploads(current_user: dict = Depends(get_current_user)):
    """List the logged-in user's own uploaded datasets (aggregated)."""
    db = get_database()
    pipeline = [
        {"$match": {"source": {"$regex": "^upload:"}, "uploaded_by": current_user["id"]}},
        {"$group": {
            "_id": "$source",
            "row_count": {"$sum": 1},
            "flagged_fraud": {"$sum": {"$cond": [{"$eq": ["$is_fraud", True]}, 1, 0]}},
            "total_amount": {"$sum": {"$ifNull": ["$amount", 0]}},
            "last_uploaded": {"$max": "$timestamp"},
        }},
        {"$sort": {"last_uploaded": -1}},
    ]
    results = await db["transactions"].aggregate(pipeline).to_list(length=200)
    uploads = []
    for r in results:
        uploads.append({
            "source": r["_id"],
            "row_count": r["row_count"],
            "flagged_fraud": r["flagged_fraud"],
            "total_amount": round(r.get("total_amount", 0), 2),
            "last_uploaded": r.get("last_uploaded"),
        })
    return uploads


@router.post("/upload-file")
async def upload_transaction_file(
    file: UploadFile = File(...),
    current_user: dict = Depends(get_current_user),
):
    """Accept a CSV or JSON file of transactions, auto-enrich, and bulk-insert into MongoDB.
    Tags every document with the uploading user's ID and email."""
    content = await file.read()
    filename = file.filename or ""
    rows = []

    def clean_float(val, default=0.0):
        if not val:
            return default
        try:
            cleaned = str(val).replace("$", "").replace(",", "").strip()
            return float(cleaned)
        except (ValueError, TypeError):
            return default

    if filename.endswith(".json"):
        try:
            text = content.decode("utf-8", errors="ignore")
            data = json.loads(text)
            if isinstance(data, dict):
                data = [data]
            rows = data
        except Exception as e:
            raise HTTPException(status_code=400, detail=f"Invalid JSON: {e}")
    elif filename.endswith(".csv") or not filename:
        try:
            text = content.decode("utf-8", errors="ignore")
            try:
                dialect = csv.Sniffer().sniff(text[:2048])
                reader = csv.DictReader(io.StringIO(text), dialect=dialect)
            except Exception:
                reader = csv.DictReader(io.StringIO(text))
            rows = list(reader)
        except Exception as e:
            raise HTTPException(status_code=400, detail=f"Invalid CSV: {e}")
    else:
        raise HTTPException(status_code=400, detail="Only .csv or .json files supported")

    if not rows:
        raise HTTPException(status_code=400, detail="File is empty or could not be parsed")

    upload_source = f"upload:{filename}"
    docs = []

    for idx, row in enumerate(rows):
        if not isinstance(row, dict):
            continue
        amount = clean_float(
            row.get("amount") or row.get("Amount") or row.get("amt")
            or row.get("TransactionAmount") or row.get("val") or 0
        )
        currency = row.get("currency") or row.get("Currency") or "USD"

        merchant_id = row.get("merchant_id") or row.get("MerchantID") or ""
        merchant_name = (
            row.get("merchant_name") or row.get("Merchant") or
            row.get("merchant") or row.get("store") or row.get("MerchantName") or
            merchant_id or random.choice(_MERCHANTS)[0]
        )
        if not merchant_id:
            merchant_id = random.choice(_MERCHANTS)[1]

        user_id = row.get("user_id") or row.get("userId") or row.get("CustomerID") or f"usr_{(idx % 50) + 1:03d}"
        account_id = row.get("account_id") or row.get("accountId") or row.get("AccountID") or f"acc_{(idx % 50) + 1:03d}"
        device_id = row.get("device_id") or row.get("DeviceID") or f"dev_upload_{random.randint(1, 64):03d}"
        raw_txn_id = row.get("txn_id") or row.get("id") or row.get("transaction_id") or row.get("TransactionID") or f"txn_{idx}"
        txn_id = f"{raw_txn_id}_{uuid.uuid4().hex[:8]}"
        txn_type = (
            row.get("type") or row.get("Type") or row.get("txn_type")
            or row.get("TransactionType") or "purchase"
        )
        is_fraud_raw = str(row.get("is_fraud") or row.get("Class") or row.get("fraud") or row.get("IsFraud") or "0")
        is_fraud = is_fraud_raw.strip() in ("1", "true", "True", "yes", "Y")
        ts = (
            row.get("timestamp") or row.get("date") or row.get("Time")
            or row.get("Date") or row.get("TransactionDate")
            or datetime.now(timezone.utc).isoformat()
        )

        city, country, lat, lon = random.choice(_CITIES)
        geo_city = row.get("city") or row.get("City") or row.get("Location") or city
        geo_country = row.get("country") or row.get("Country") or country
        geo_lat = clean_float(row.get("latitude") or row.get("lat") or lat, lat)
        geo_lon = clean_float(row.get("longitude") or row.get("lon") or lon, lon)
        geo_ip = row.get("ip") or row.get("IP Address") or row.get("ip_address") or row.get("IPAddress") or "0.0.0.0"

        doc = {
            "txn_id": str(txn_id),
            "account_id": str(account_id),
            "user_id": str(user_id),
            "amount": amount,
            "currency": str(currency),
            "merchant_id": str(merchant_id),
            "merchant_name": str(merchant_name),
            "device_id": str(device_id),
            "session_id": f"sess_upload_{uuid.uuid4().hex[:6]}",
            "geo": {"ip": str(geo_ip), "country": str(geo_country), "city": str(geo_city),
                    "latitude": geo_lat, "longitude": geo_lon},
            "timestamp": str(ts),
            "type": str(txn_type),
            "is_fraud": is_fraud,
            "is_real": True,
            "is_simulated": False,
            "source": upload_source,
            "uploaded_by": current_user["id"],
            "uploader_email": current_user["email"],
        }

        # Preserve extra CSV columns
        _mapped_keys = {
            "amount", "Amount", "amt", "TransactionAmount", "val",
            "currency", "Currency",
            "merchant_name", "Merchant", "merchant", "store", "MerchantName",
            "merchant_id", "MerchantID",
            "user_id", "userId", "CustomerID",
            "account_id", "accountId", "AccountID",
            "device_id", "DeviceID",
            "txn_id", "id", "transaction_id", "TransactionID",
            "type", "Type", "txn_type", "TransactionType",
            "is_fraud", "Class", "fraud", "IsFraud",
            "timestamp", "date", "Time", "Date", "TransactionDate",
            "city", "City", "Location", "country", "Country",
            "latitude", "lat", "longitude", "lon",
            "ip", "IP Address", "ip_address", "IPAddress",
        }
        extras = {}
        for k, v in row.items():
            if k not in _mapped_keys and v:
                extras[k] = v
        if extras:
            doc["extra"] = extras

        docs.append(doc)

    if not docs:
        raise HTTPException(status_code=400, detail="No valid transaction rows found in file")

    # Delete previous upload with same source for THIS user only
    from pymongo.errors import BulkWriteError
    db = get_database()
    await db["transactions"].delete_many({
        "source": upload_source,
        "uploaded_by": current_user["id"],
    })

    inserted_count = 0
    try:
        result = await db["transactions"].insert_many(docs, ordered=False)
        inserted_count = len(result.inserted_ids)
    except BulkWriteError as bwe:
        inserted_count = bwe.details.get("nInserted", 0)
        logger.warning(f"BulkWriteError during upload: {inserted_count} inserted, some duplicates skipped")

    for doc in docs:
        doc.pop("_id", None)

    return {
        "status": "success",
        "inserted": inserted_count,
        "source": upload_source,
        "preview": docs[:3]
    }


@router.post("/score-uploaded")
async def score_uploaded_dataset(
    source: str = Query(..., description="Source tag, e.g. 'upload:filename.csv'"),
    current_user: dict = Depends(get_current_user),
):
    """Run every transaction in an uploaded dataset through the real ShieldGPT pipeline.
    Persists Decision documents, broadcasts each over WebSocket, returns results."""
    from app.orchestrator.shieldgpt import ShieldGPTOrchestrator
    from app.orchestrator.llm_client import LLMClient
    from app.models.schemas import ScoreRequest

    db = get_database()
    query = {"source": source}
    if current_user.get("role") != "admin":
        query["uploaded_by"] = current_user["id"]

    cursor = db["transactions"].find(query).limit(10000)
    txns = await cursor.to_list(length=10000)

    if not txns:
        raise HTTPException(status_code=404, detail="No transactions found for this source")

    llm = LLMClient()
    shield = ShieldGPTOrchestrator(llm)
    results = []

    for txn in txns:
        txn_id = txn.get("txn_id")
        if not txn_id:
            continue

        try:
            score_resp = await shield.analyze_transaction(
                ScoreRequest(txn_id=txn_id, include_explanation=False)
            )
            results.append(score_resp.model_dump())
        except Exception as e:
            logger.warning(f"Scoring failed for {txn_id}: {e}")
            # Fallback minimal decision
            results.append({
                "txn_id": txn_id,
                "decision": "ALLOW",
                "risk_score": 0.0,
                "confidence": 0.0,
                "reasons": [f"Scoring error: {str(e)[:100]}"],
                "explanation": "Scoring failed — fallback ALLOW",
                "engine_scores": {},
            })

    return {
        "source": source,
        "scored": len(results),
        "results": results,
    }


@router.get("/{txn_id}")
async def get_transaction(txn_id: str):
    """Get a single transaction."""
    txn = await find_one("transactions", {"txn_id": txn_id})
    if not txn:
        raise HTTPException(status_code=404, detail="Transaction not found")
    txn.pop("_id", None)
    return txn


@router.websocket("/stream")
async def transaction_stream(websocket: WebSocket):
    """WebSocket endpoint for live transaction/decision feed."""
    manager = get_manager()
    await manager.connect(websocket)
    try:
        while True:
            data = await websocket.receive_text()
            # Client pings to keep alive
    except WebSocketDisconnect:
        manager.disconnect(websocket)
    except Exception:
        manager.disconnect(websocket)
