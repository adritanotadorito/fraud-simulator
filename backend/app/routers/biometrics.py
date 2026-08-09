from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from app.models.schemas import EngineScoreResponse
from app.engines.biometrics import BiometricsEngine
from app.database import find_one

router = APIRouter(prefix="/api/biometrics", tags=["biometrics"])

class BiometricsScoreRequest(BaseModel):
    session_id: str

@router.post("/score", response_model=EngineScoreResponse)
async def score_biometrics(request: BiometricsScoreRequest):
    session = await find_one("sessions", {"session_id": request.session_id})
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    session.pop("_id", None)
    
    engine = BiometricsEngine()
    score = await engine.score(session, session.get("user_id"))
    return score
