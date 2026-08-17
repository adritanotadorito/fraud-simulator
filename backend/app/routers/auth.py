"""
auth.py router — signup / login / me endpoints.

Bootstrap rule: the very first account created on the deployment becomes admin;
every signup after that is forced to role="user" — the role is never trusted
from the client payload after the first user.
"""

import logging
from uuid import uuid4
from datetime import datetime, timezone

from fastapi import APIRouter, HTTPException, Depends

from app.database import find_one, insert_one, count_documents
from app.auth.security import hash_password, verify_password, create_access_token
from app.auth.dependencies import get_current_user

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/auth", tags=["Auth"])


@router.post("/signup")
async def signup(payload: dict):
    """Register a new account.  First-ever account = admin."""
    name = (payload.get("name") or "").strip()
    email = (payload.get("email") or "").strip().lower()
    password = payload.get("password") or ""

    if not email or not password:
        raise HTTPException(status_code=400, detail="Email and password are required")
    if len(password) < 6:
        raise HTTPException(status_code=400, detail="Password must be at least 6 characters")

    existing = await find_one("app_users", {"email": email})
    if existing:
        raise HTTPException(status_code=409, detail="Email already registered")

    # Bootstrap: first user ever → admin, all others → user
    total_users = await count_documents("app_users", {})
    role = "admin" if total_users == 0 else "user"

    user_id = str(uuid4())
    user_doc = {
        "id": user_id,
        "name": name or email.split("@")[0],
        "email": email,
        "password_hash": hash_password(password),
        "role": role,
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    await insert_one("app_users", user_doc)
    logger.info(f"New user registered: {email} (role={role})")

    token = create_access_token({"sub": user_id, "email": email, "role": role})
    return {
        "token": token,
        "user": {
            "id": user_id,
            "name": user_doc["name"],
            "email": email,
            "role": role,
        },
    }


@router.post("/login")
async def login(payload: dict):
    """Authenticate and return a JWT."""
    email = (payload.get("email") or "").strip().lower()
    password = payload.get("password") or ""

    if not email or not password:
        raise HTTPException(status_code=400, detail="Email and password are required")

    user = await find_one("app_users", {"email": email})
    if not user:
        raise HTTPException(status_code=401, detail="Invalid email or password")

    if not verify_password(password, user["password_hash"]):
        raise HTTPException(status_code=401, detail="Invalid email or password")

    token = create_access_token({
        "sub": user["id"],
        "email": user["email"],
        "role": user["role"],
    })

    return {
        "token": token,
        "user": {
            "id": user["id"],
            "name": user.get("name", ""),
            "email": user["email"],
            "role": user["role"],
        },
    }


@router.get("/me")
async def get_me(current_user: dict = Depends(get_current_user)):
    """Return the authenticated user's profile."""
    return {
        "id": current_user["id"],
        "name": current_user.get("name", ""),
        "email": current_user["email"],
        "role": current_user["role"],
    }
