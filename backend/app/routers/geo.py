from fastapi import APIRouter
from pydantic import BaseModel
from typing import Optional
from datetime import datetime
from app.models.schemas import EngineScoreResponse, GeoInfo
from app.engines.geo import GeolocationEngine

router = APIRouter(prefix="/api/geo", tags=["geo"])

class GeoScoreRequest(BaseModel):
    user_id: str
    geo: GeoInfo
    timestamp: Optional[datetime] = None

@router.post("/score", response_model=EngineScoreResponse)
async def score_geo(request: GeoScoreRequest):
    engine = GeolocationEngine()
    score = await engine.score(request.geo, request.user_id, request.timestamp)
    return score
