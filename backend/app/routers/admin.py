"""
admin.py router — admin-only endpoints for user management and platform stats.
All endpoints require `require_admin` dependency.
"""

import logging
from fastapi import APIRouter, HTTPException, Depends, Query

from app.database import find_many, find_one, get_database, count_documents
from app.auth.dependencies import require_admin

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/admin", tags=["Admin"], dependencies=[Depends(require_admin)])


@router.get("/users")
async def list_users():
    """List every registered account."""
    users = await find_many("app_users", {}, limit=1000, sort=[("created_at", -1)])
    for u in users:
        u.pop("_id", None)
        u.pop("password_hash", None)
    return users


@router.patch("/users/{user_id}/role")
async def update_user_role(user_id: str, role: str = Query(..., pattern="^(admin|user)$")):
    """Promote or demote a user."""
    from app.database import update_one
    user = await find_one("app_users", {"id": user_id})
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    await update_one("app_users", {"id": user_id}, {"$set": {"role": role}})
    logger.info(f"User {user_id} role changed to {role}")
    return {"id": user_id, "role": role, "message": f"Role updated to {role}"}


@router.get("/uploads")
async def list_all_uploads():
    """Every uploaded dataset across every user — aggregated."""
    db = get_database()
    pipeline = [
        {"$match": {"source": {"$regex": "^upload:"}}},
        {"$group": {
            "_id": {"source": "$source", "uploaded_by": {"$ifNull": ["$uploaded_by", "unknown"]}},
            "row_count": {"$sum": 1},
            "flagged_fraud": {"$sum": {"$cond": [{"$eq": ["$is_fraud", True]}, 1, 0]}},
            "total_amount": {"$sum": {"$ifNull": ["$amount", 0]}},
            "last_uploaded": {"$max": "$timestamp"},
            "uploader_email": {"$first": {"$ifNull": ["$uploader_email", "unknown"]}},
        }},
        {"$sort": {"last_uploaded": -1}},
    ]
    results = await db["transactions"].aggregate(pipeline).to_list(length=500)
    uploads = []
    for r in results:
        uploads.append({
            "source": r["_id"]["source"],
            "uploaded_by": r["_id"]["uploaded_by"],
            "uploader_email": r.get("uploader_email", "unknown"),
            "row_count": r["row_count"],
            "flagged_fraud": r["flagged_fraud"],
            "total_amount": round(r.get("total_amount", 0), 2),
            "last_uploaded": r.get("last_uploaded"),
        })
    return uploads


@router.get("/stats")
async def platform_stats():
    """Platform-wide totals."""
    db = get_database()
    total_users = await db["app_users"].count_documents({})
    total_txns = await db["transactions"].count_documents({"source": {"$regex": "^upload:"}})
    total_decisions = await db["decisions"].count_documents({})
    blocked = await db["decisions"].count_documents({"decision": "BLOCK"})
    flagged = await db["decisions"].count_documents({"decision": "FLAG"})

    return {
        "total_users": total_users,
        "uploaded_transactions": total_txns,
        "total_decisions": total_decisions,
        "blocked": blocked,
        "flagged": flagged,
    }
