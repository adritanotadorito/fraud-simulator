from fastapi import APIRouter, HTTPException, Query
from typing import Optional
import logging

from app.models.schemas import ScoreRequest, ScoreResponse
from app.orchestrator.shieldgpt import ShieldGPTOrchestrator
from app.orchestrator.llm_client import LLMClient
from app.database import find_many, find_one

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/shield", tags=["Shield - Blue Team"])


@router.post("/decision", response_model=ScoreResponse)
async def score_transaction(request: ScoreRequest):
    """Score a transaction through ShieldGPT."""
    llm = LLMClient()
    shield = ShieldGPTOrchestrator(llm)
    try:
        return await shield.analyze_transaction(request)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.get("/decisions")
async def list_decisions(
    limit: int = Query(50, ge=1, le=200),
    decision_type: Optional[str] = None
):
    """List recent decisions."""
    query = {}
    if decision_type:
        query["decision"] = decision_type.upper()
    results = await find_many("decisions", query, limit=limit, sort=[("created_at", -1)])
    for r in results:
        r.pop("_id", None)
    return results


@router.get("/decisions/{decision_id}")
async def get_decision(decision_id: str):
    """Get a single decision."""
    result = await find_one("decisions", {"decision_id": decision_id})
    if not result:
        raise HTTPException(status_code=404, detail="Decision not found")
    result.pop("_id", None)
    return result
