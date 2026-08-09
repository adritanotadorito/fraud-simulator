from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from app.models.schemas import EngineScoreResponse
from app.engines.device import DeviceEngine
from app.database import find_one

router = APIRouter(prefix="/api/device", tags=["device"])

class DeviceScoreRequest(BaseModel):
    device_id: str
    user_id: str

@router.post("/score", response_model=EngineScoreResponse)
async def score_device(request: DeviceScoreRequest):
    device = await find_one("devices", {"device_id": request.device_id, "user_id": request.user_id})
    if not device:
        raise HTTPException(status_code=404, detail="Device not found")
    device.pop("_id", None)
        
    engine = DeviceEngine()
    score = await engine.score(device, request.user_id)
    return score
