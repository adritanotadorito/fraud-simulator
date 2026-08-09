from fastapi import APIRouter, HTTPException, Query
from typing import Optional, List
from app.models.schemas import EngineScoreResponse, ThreatIntelEntry
from app.engines.threat_intel import ThreatIntelEngine
from app.database import find_many, insert_one

router = APIRouter(prefix="/api/threat-intel", tags=["threat-intel"])

@router.get("/lookup", response_model=EngineScoreResponse)
async def lookup_entity(ip: Optional[str] = None, device_id: Optional[str] = None, account_id: Optional[str] = None, merchant_id: Optional[str] = None):
    if not any([ip, device_id, account_id, merchant_id]):
        raise HTTPException(status_code=400, detail="At least one entity identifier required")
        
    engine = ThreatIntelEngine()
    score = await engine.lookup(ip=ip, device_id=device_id, account_id=account_id, merchant_id=merchant_id)
    return score

@router.get("/watchlist", response_model=List[ThreatIntelEntry])
async def list_watchlist():
    entries = await find_many("threat_intel", {})
    for e in entries:
        e.pop("_id", None)
    return entries

@router.post("/watchlist", response_model=ThreatIntelEntry)
async def add_watchlist(entry: ThreatIntelEntry):
    result = await insert_one("threat_intel", entry.model_dump())
    if not result:
        raise HTTPException(status_code=500, detail="Failed to add entry")
    return entry
