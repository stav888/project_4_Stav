"""
Authentication Endpoints
Handles user login and token generation.
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
import logging
import os
import dal_users
from auth import create_access_token

logger = logging.getLogger('app')
router = APIRouter(prefix="/auth", tags=["auth"])


class LoginRequest(BaseModel):
    """Request model for login."""
    username: str
    password: str


def flush_logs():
    """Flush all log handlers to ensure logs are written to disk."""
    for handler in logging.getLogger().handlers:
        handler.flush()


@router.post("/login")
def login(credentials: LoginRequest):
    """Login a user and return JWT token."""
    logger.info(f"🔐 POST /auth/login - Login attempt: {credentials.username}")
    if not dal_users.login_user(credentials.username, credentials.password):
        logger.warning(f"❌ POST /auth/login - Invalid credentials: {credentials.username}")
        flush_logs()
        raise HTTPException(status_code=401, detail="Invalid username or password")

    user = dal_users.get_user_by_username(credentials.username)
    
    # Safety check: ensure user exists
    if not user:
        logger.error(f"❌ POST /auth/login - User disappeared after login: {credentials.username}")
        flush_logs()
        raise HTTPException(status_code=500, detail="Authentication error")
    
    token = create_access_token(credentials.username)
    logger.info(f"✅ POST /auth/login - Login successful: {credentials.username}")
    flush_logs()
    return {"access_token": token, "token_type": "bearer", "user_name": user["user_name"], "id": user["id"]}
