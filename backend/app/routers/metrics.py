from fastapi import APIRouter
from typing import List
from app.models.schemas import MetricsResponse, ModelMetrics
from app.database import find_many, count_documents

router = APIRouter(prefix="/api/metrics", tags=["metrics"])

@router.get("/model", response_model=MetricsResponse)
async def get_model_metrics():
    return MetricsResponse(metrics=[])

@router.get("/model/history", response_model=List[ModelMetrics])
async def get_metrics_history():
    metrics = await find_many("model_metrics", {}, sort=[("timestamp", -1)])
    for m in metrics:
        m.pop("_id", None)
    return metrics

@router.get("/dashboard")
async def get_dashboard():
    total_txns = await count_documents("transactions", {})
    total_attacks = await count_documents("fraud_events", {})
    blocked = await count_documents("decisions", {"decision": "BLOCK"})
    flagged = await count_documents("decisions", {"decision": "FLAG"})
    allowed = await count_documents("decisions", {"decision": "ALLOW"})
    
    return {
        "total_transactions": total_txns,
        "total_attacks": total_attacks,
        "blocked": blocked,
        "flagged": flagged,
        "allowed": allowed,
        "avg_risk_score": 0.5,
        "avg_latency": 150,
        "active_personas": 3
    }
