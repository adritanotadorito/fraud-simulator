from fastapi import APIRouter, HTTPException, Query, WebSocket, WebSocketDisconnect
from typing import Optional
import logging

from app.database import find_many, find_one, insert_one
from app.ws.manager import get_manager

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/transactions", tags=["Transactions"])


@router.get("/")
async def list_transactions(
    limit: int = Query(50, ge=1, le=500),
    offset: int = Query(0, ge=0),
    account_id: Optional[str] = None,
    user_id: Optional[str] = None
):
    """List recent transactions."""
    query = {}
    if account_id:
        query["account_id"] = account_id
    if user_id:
        query["user_id"] = user_id
    results = await find_many("transactions", query, limit=limit, sort=[("timestamp", -1)])
    for r in results:
        r.pop("_id", None)
    return results


@router.get("/{txn_id}")
async def get_transaction(txn_id: str):
    """Get a single transaction."""
    txn = await find_one("transactions", {"txn_id": txn_id})
    if not txn:
        raise HTTPException(status_code=404, detail="Transaction not found")
    txn.pop("_id", None)
    return txn


@router.websocket("/stream")
async def transaction_stream(websocket: WebSocket):
    """WebSocket endpoint for live transaction/decision feed."""
    manager = get_manager()
    await manager.connect(websocket)
    try:
        while True:
            data = await websocket.receive_text()
            # Client pings to keep alive
    except WebSocketDisconnect:
        manager.disconnect(websocket)
    except Exception:
        manager.disconnect(websocket)
