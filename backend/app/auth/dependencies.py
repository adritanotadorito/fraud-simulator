"""
dependencies.py — FastAPI dependencies for auth: get_current_user, require_admin.
"""

import logging
from fastapi import Depends, HTTPException, Request

from app.auth.security import decode_access_token
from app.database import find_one

logger = logging.getLogger(__name__)


async def get_current_user(request: Request) -> dict:
    """Extract + validate the Bearer token, return the app_users document."""
    auth_header = request.headers.get("Authorization", "")
    if not auth_header.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Missing or invalid Authorization header")

    token = auth_header.split(" ", 1)[1]
    try:
        payload = decode_access_token(token)
    except Exception:
        raise HTTPException(status_code=401, detail="Invalid or expired token")

    user_id = payload.get("sub")
    if not user_id:
        raise HTTPException(status_code=401, detail="Invalid token payload")

    user = await find_one("app_users", {"id": user_id})
    if not user:
        raise HTTPException(status_code=401, detail="User not found")

    user.pop("_id", None)
    user.pop("password_hash", None)
    return user


async def require_admin(user: dict = Depends(get_current_user)) -> dict:
    """Raise 403 unless the authenticated user has role=admin."""
    if user.get("role") != "admin":
        raise HTTPException(status_code=403, detail="Admin access required")
    return user
