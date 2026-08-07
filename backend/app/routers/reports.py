from fastapi import APIRouter, Query, HTTPException
from fastapi.responses import StreamingResponse
from typing import Optional
from datetime import datetime
from app.database import find_many, find_one
import io
import csv

router = APIRouter(prefix="/api/reports", tags=["reports"])

@router.get("/incident")
async def generate_incident_report(format: str = Query("json"), start_date: Optional[datetime] = None, end_date: Optional[datetime] = None):
    query = {}
    events = await find_many("fraud_events", query)
    
    if format == "csv":
        output = io.StringIO()
        writer = csv.writer(output)
        writer.writerow(["event_id", "timestamp", "persona", "status"])
        for event in events:
            writer.writerow([event.get("event_id"), event.get("timestamp"), event.get("persona"), event.get("status")])
        output.seek(0)
        return StreamingResponse(iter([output.getvalue()]), media_type="text/csv", headers={"Content-Disposition": "attachment; filename=incident_report.csv"})
        
    for event in events:
        event.pop("_id", None)
    return events

@router.get("/incident/{event_id}")
async def get_incident_detail(event_id: str):
    event = await find_one("fraud_events", {"event_id": event_id})
    if not event:
        raise HTTPException(status_code=404, detail="Event not found")
    event.pop("_id", None)
    return event

@router.get("/summary")
async def get_summary_report():
    decisions = await find_many("decisions", {})
    fraud_events = await find_many("fraud_events", {})
    return {
        "summary": "Overall summary report",
        "total_decisions": len(decisions),
        "total_fraud_events": len(fraud_events)
    }
