from fastapi import APIRouter, Query
from typing import Optional
from app.models.schemas import ModelMetrics
from app.database import find_many, find_one, count_documents, insert_one, is_connected
import logging

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/metrics", tags=["Model Metrics"])


@router.get("/model")
async def get_model_metrics():
    """Get latest model metrics."""
    metrics = await find_many("model_metrics", {}, limit=1, sort=[("timestamp", -1)])
    if metrics:
        metrics[0].pop("_id", None)
        return {"latest": metrics[0]}
    return {"latest": None, "message": "No model metrics recorded yet"}


@router.get("/model/history")
async def get_metrics_history(limit: int = Query(20, ge=1, le=100)):
    """Get model metrics history."""
    metrics = await find_many("model_metrics", {}, limit=limit, sort=[("timestamp", -1)])
    for m in metrics:
        m.pop("_id", None)
    return {"history": metrics, "count": len(metrics)}


@router.get("/dashboard")
async def get_dashboard():
    """Get real-time dashboard metrics computed from actual DB data."""
    total_txns = await count_documents("transactions", {})
    total_attacks = await count_documents("fraud_events", {})
    total_decisions = await count_documents("decisions", {})
    blocked = await count_documents("decisions", {"decision": "BLOCK"})
    flagged = await count_documents("decisions", {"decision": "FLAG"})
    allowed = await count_documents("decisions", {"decision": "ALLOW"})

    # Compute average risk score from recent decisions
    recent_decisions = await find_many("decisions", {}, limit=100, sort=[("created_at", -1)])
    avg_risk = 0.0
    avg_latency = 0.0
    if recent_decisions:
        risk_scores = [d.get("risk_score", 0) for d in recent_decisions]
        avg_risk = round(sum(risk_scores) / len(risk_scores), 4)
        latencies = [
            d.get("engine_scores", {}).get("fusion", {}).get("latency_ms", 0)
            for d in recent_decisions
        ]
        latencies = [l for l in latencies if l > 0]
        avg_latency = round(sum(latencies) / len(latencies), 1) if latencies else 0

    # Count active personas
    events = await find_many("fraud_events", {}, limit=1000)
    active_personas = len(set(e.get("persona", "") for e in events))

    # Overall detection rate
    detection_rate = 0.0
    if total_decisions > 0:
        detection_rate = round((blocked + flagged) / total_decisions, 4)

    return {
        "total_transactions": total_txns,
        "total_attacks": total_attacks,
        "total_decisions": total_decisions,
        "blocked": blocked,
        "flagged": flagged,
        "allowed": allowed,
        "detection_rate": detection_rate,
        "avg_risk_score": avg_risk,
        "avg_latency_ms": avg_latency,
        "active_personas": active_personas,
        "db_connected": is_connected()
    }


@router.post("/compute")
async def compute_and_store_metrics():
    """Compute current model metrics from decisions and store in model_metrics collection."""
    decisions = await find_many("decisions", {}, limit=5000)
    if not decisions:
        return {"message": "No decisions to compute metrics from"}

    # Match decisions to transactions to get ground truth
    total = len(decisions)
    tp = fp = tn = fn = 0

    for d in decisions:
        txn_id = d.get("txn_id", "")
        txn = await find_one("transactions", {"txn_id": txn_id})
        is_fraud = txn.get("is_fraud", False) if txn else False
        predicted_fraud = d.get("decision") in ["BLOCK", "FLAG"]

        if is_fraud and predicted_fraud:
            tp += 1
        elif is_fraud and not predicted_fraud:
            fn += 1
        elif not is_fraud and predicted_fraud:
            fp += 1
        else:
            tn += 1

    accuracy = (tp + tn) / total if total > 0 else 0
    precision = tp / (tp + fp) if (tp + fp) > 0 else 0
    recall = tp / (tp + fn) if (tp + fn) > 0 else 0
    f1 = 2 * precision * recall / (precision + recall) if (precision + recall) > 0 else 0

    # Approximate ROC AUC from risk scores
    fraud_scores = []
    legit_scores = []
    for d in decisions:
        txn = await find_one("transactions", {"txn_id": d.get("txn_id", "")})
        is_fraud = txn.get("is_fraud", False) if txn else False
        if is_fraud:
            fraud_scores.append(d.get("risk_score", 0))
        else:
            legit_scores.append(d.get("risk_score", 0))

    roc_auc = 0.5
    if fraud_scores and legit_scores:
        avg_fraud = sum(fraud_scores) / len(fraud_scores)
        avg_legit = sum(legit_scores) / len(legit_scores)
        roc_auc = min(0.5 + abs(avg_fraud - avg_legit), 1.0)

    # Average latency
    latencies = [
        d.get("engine_scores", {}).get("fusion", {}).get("latency_ms", 0)
        for d in decisions
    ]
    latencies = [l for l in latencies if l > 0]
    avg_latency = sum(latencies) / len(latencies) if latencies else 0

    metrics = ModelMetrics(
        accuracy=round(accuracy, 4),
        precision=round(precision, 4),
        recall=round(recall, 4),
        f1=round(f1, 4),
        roc_auc=round(roc_auc, 4),
        latency_ms=round(avg_latency, 1),
        total_transactions=total,
        true_positives=tp,
        false_positives=fp,
        true_negatives=tn,
        false_negatives=fn
    )

    await insert_one("model_metrics", metrics.model_dump())
    return {"message": "Metrics computed and stored", "metrics": metrics.model_dump()}
