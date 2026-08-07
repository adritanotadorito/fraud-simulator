from fastapi import APIRouter, Query, HTTPException
from fastapi.responses import StreamingResponse
from typing import Optional
from datetime import datetime, timezone
from app.database import find_many, find_one, count_documents
import io
import csv
import json
import logging

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/reports", tags=["Reports"])


@router.get("/incident")
async def generate_incident_report(
    format: str = Query("json", pattern="^(json|csv)$"),
    limit: int = Query(100, ge=1, le=1000),
    persona: Optional[str] = None,
    outcome: Optional[str] = None
):
    """Generate an incident report in JSON or CSV format."""
    query = {}
    if persona:
        query["persona"] = persona
    if outcome:
        query["outcome"] = outcome

    events = await find_many("fraud_events", query, limit=limit, sort=[("created_at", -1)])

    # Enrich with decision data
    enriched = []
    for event in events:
        event.pop("_id", None)
        txn_ids = event.get("txn_ids", [])
        decisions = []
        for txn_id in txn_ids[:5]:  # Limit lookups
            dec = await find_one("decisions", {"txn_id": txn_id})
            if dec:
                dec.pop("_id", None)
                decisions.append({
                    "txn_id": dec.get("txn_id"),
                    "decision": dec.get("decision"),
                    "risk_score": dec.get("risk_score"),
                    "reasons": dec.get("reasons", [])[:3]
                })
        event["decisions"] = decisions
        enriched.append(event)

    if format == "csv":
        output = io.StringIO()
        writer = csv.writer(output)
        writer.writerow([
            "event_id", "persona", "strategy", "round", "outcome",
            "num_transactions", "created_at", "top_decision", "max_risk_score"
        ])
        for event in enriched:
            decisions = event.get("decisions", [])
            top_dec = decisions[0]["decision"] if decisions else "N/A"
            max_risk = max((d.get("risk_score", 0) for d in decisions), default=0)
            writer.writerow([
                event.get("event_id"), event.get("persona"),
                event.get("strategy", "")[:80], event.get("round"),
                event.get("outcome"), len(event.get("txn_ids", [])),
                event.get("created_at"), top_dec, round(max_risk, 4)
            ])
        output.seek(0)
        return StreamingResponse(
            iter([output.getvalue()]),
            media_type="text/csv",
            headers={"Content-Disposition": "attachment; filename=incident_report.csv"}
        )

    return {"incidents": enriched, "count": len(enriched)}


@router.get("/incident/{event_id}")
async def get_incident_detail(event_id: str):
    """Get detailed incident report for a specific event."""
    event = await find_one("fraud_events", {"event_id": event_id})
    if not event:
        raise HTTPException(status_code=404, detail="Event not found")
    event.pop("_id", None)

    # Fetch all related transactions and decisions
    txn_ids = event.get("txn_ids", [])
    transactions = []
    decisions = []
    for txn_id in txn_ids:
        txn = await find_one("transactions", {"txn_id": txn_id})
        if txn:
            txn.pop("_id", None)
            transactions.append(txn)
        dec = await find_one("decisions", {"txn_id": txn_id})
        if dec:
            dec.pop("_id", None)
            decisions.append(dec)

    return {
        "event": event,
        "transactions": transactions,
        "decisions": decisions,
        "summary": {
            "total_txns": len(transactions),
            "total_amount": sum(t.get("amount", 0) for t in transactions),
            "blocked": sum(1 for d in decisions if d.get("decision") == "BLOCK"),
            "flagged": sum(1 for d in decisions if d.get("decision") == "FLAG"),
            "allowed": sum(1 for d in decisions if d.get("decision") == "ALLOW"),
            "avg_risk": round(
                sum(d.get("risk_score", 0) for d in decisions) / max(len(decisions), 1), 4
            )
        }
    }


@router.get("/summary")
async def get_summary_report():
    """Get overall system summary report."""
    total_events = await count_documents("fraud_events", {})
    total_decisions = await count_documents("decisions", {})
    total_txns = await count_documents("transactions", {})
    blocked = await count_documents("decisions", {"decision": "BLOCK"})
    flagged = await count_documents("decisions", {"decision": "FLAG"})
    allowed = await count_documents("decisions", {"decision": "ALLOW"})

    # Per-persona breakdown
    events = await find_many("fraud_events", {}, limit=5000)
    persona_stats = {}
    for e in events:
        p = e.get("persona", "unknown")
        if p not in persona_stats:
            persona_stats[p] = {"total": 0, "blocked": 0, "flagged": 0, "allowed": 0, "pending": 0}
        persona_stats[p]["total"] += 1
        outcome = e.get("outcome", "pending")
        if outcome in persona_stats[p]:
            persona_stats[p][outcome] += 1

    return {
        "total_fraud_events": total_events,
        "total_decisions": total_decisions,
        "total_transactions": total_txns,
        "decision_breakdown": {
            "blocked": blocked,
            "flagged": flagged,
            "allowed": allowed
        },
        "detection_rate": round((blocked + flagged) / max(total_decisions, 1), 4),
        "persona_breakdown": persona_stats
    }
