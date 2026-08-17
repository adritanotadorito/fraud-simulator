from fastapi import APIRouter, HTTPException, Query
from typing import Optional
import logging

from app.models.schemas import AttackRequest, AttackResponse, MemoryResponse, ScoreRequest
from app.orchestrator.fraudgpt import FraudGPTOrchestrator
from app.orchestrator.shieldgpt import ShieldGPTOrchestrator
from app.orchestrator.llm_client import LLMClient
from app.database import find_many, find_one

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/fraud", tags=["Fraud - Red Team"])


def _get_orchestrators():
    llm = LLMClient()
    return FraudGPTOrchestrator(llm), ShieldGPTOrchestrator(llm)


@router.post("/attack", response_model=AttackResponse)
async def trigger_attack(request: AttackRequest):
    """Trigger a FraudGPT attack round and have ShieldGPT defend."""
    fraud_gpt, shield_gpt = _get_orchestrators()
    attack = await fraud_gpt.launch_attack(request)

    outcomes = []
    for txn_id in attack.transactions_generated:
        try:
            decision = await shield_gpt.analyze_transaction(
                ScoreRequest(txn_id=txn_id, include_explanation=True)
            )
            outcomes.append(decision.decision)
        except Exception as e:
            logger.error(f"Shield analysis failed for {txn_id}: {e}")

    if outcomes:
        if "BLOCK" in outcomes:
            overall = "blocked"
        elif "FLAG" in outcomes:
            overall = "flagged"
        else:
            overall = "allowed"
        await fraud_gpt.update_memory(attack.event_id, overall)

    return attack


@router.get("/memory", response_model=MemoryResponse)
async def get_memory():
    """Get FraudGPT's learned strategy weights."""
    fraud_gpt, _ = _get_orchestrators()
    return await fraud_gpt.get_memory()


@router.get("/events")
async def list_events(
    limit: int = Query(50, ge=1, le=200),
    round: Optional[int] = None,
    persona: Optional[str] = None
):
    """List fraud events."""
    query = {}
    if round is not None:
        query["round"] = round
    if persona:
        query["persona"] = persona
    events = await find_many("fraud_events", query, limit=limit, sort=[("created_at", -1)])
    # Remove MongoDB _id for JSON serialization
    for e in events:
        e.pop("_id", None)
    return events


@router.get("/events/{event_id}")
async def get_event(event_id: str):
    """Get a single fraud event."""
    event = await find_one("fraud_events", {"event_id": event_id})
    if not event:
        raise HTTPException(status_code=404, detail="Fraud event not found")
    event.pop("_id", None)
    return event


@router.post("/simulate-round")
async def simulate_round(persona: Optional[str] = None):
    """Run a full adversarial round: FraudGPT attacks, ShieldGPT defends."""
    fraud_gpt, shield_gpt = _get_orchestrators()

    request = AttackRequest(persona=persona)
    attack = await fraud_gpt.launch_attack(request)

    decisions = []
    blocked = flagged = allowed = 0

    import uuid
    from datetime import datetime, timezone
    from app.ws.manager import get_manager

    manager = get_manager()

    for txn_id in attack.transactions_generated:
        try:
            decision = await shield_gpt.analyze_transaction(
                ScoreRequest(txn_id=txn_id, include_explanation=True)
            )
            decisions.append(decision.model_dump())
            if decision.decision == "BLOCK":
                blocked += 1
            elif decision.decision == "FLAG":
                flagged += 1
            else:
                allowed += 1

            # Fetch transaction details for live feed
            txn_doc = await find_one("transactions", {"txn_id": txn_id})
            merchant_name = txn_doc.get("merchant_name", "Online Store") if txn_doc else "Online Store"
            amount = txn_doc.get("amount", 100.0) if txn_doc else 100.0

            event_payload = {
                "event_id": f"evt_{uuid.uuid4().hex[:8]}",
                "transaction": {
                    "transaction_id": txn_id,
                    "merchant": merchant_name,
                    "amount": amount,
                    "user_id": txn_doc.get("user_id", "usr_sim") if txn_doc else "usr_sim",
                    "account_id": txn_doc.get("account_id", "acc_sim") if txn_doc else "acc_sim",
                    "timestamp": txn_doc.get("timestamp", datetime.now(timezone.utc).isoformat()) if txn_doc else datetime.now(timezone.utc).isoformat()
                },
                "shieldgpt": decision.model_dump(),
                "fraudgpt": {
                    "persona": attack.persona
                }
            }

            await manager.broadcast(event_payload)

        except Exception as e:
            logger.error(f"Analysis error for {txn_id}: {e}")

    if blocked > 0:
        overall = "blocked"
    elif flagged > 0:
        overall = "flagged"
    else:
        overall = "allowed"
    await fraud_gpt.update_memory(attack.event_id, overall)

    return {
        "attack": attack.model_dump(),
        "decisions": decisions,
        "round_summary": {
            "blocked": blocked, "flagged": flagged,
            "allowed": allowed, "total": len(decisions)
        }
    }
