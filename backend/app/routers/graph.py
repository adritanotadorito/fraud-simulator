from fastapi import APIRouter, Query, HTTPException
from pydantic import BaseModel
from typing import Optional, Dict, Any, List
from app.models.schemas import EngineScoreResponse
from app.engines.graph import GraphEngine

router = APIRouter(prefix="/api/graph", tags=["graph"])

class GraphScoreRequest(BaseModel):
    user_id: str
    device_id: str

@router.post("/score", response_model=EngineScoreResponse)
async def score_graph(request: GraphScoreRequest):
    engine = GraphEngine()
    score = await engine.score(request.user_id, request.device_id)
    return score

@router.get("/relationships")
async def get_relationships(user_id: Optional[str] = None, depth: int = Query(2)):
    engine = GraphEngine()
    data = await engine.get_relationships(user_id, depth)
    return data

@router.get("/fraud-rings")
async def detect_fraud_rings():
    engine = GraphEngine()
    rings = await engine.detect_fraud_rings()
    return rings
