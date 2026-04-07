"""
Authentication endpoints - login and token generation.
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

import dal_users
from auth import create_access_token
from log import logger

router = APIRouter(prefix="/auth", tags=["auth"])


# Request model for login credentials
class LoginRequest(BaseModel):
    username: str = Field(..., min_length=1, max_length=255)
    password: str = Field(..., min_length=1)


# Login endpoint - authenticate user and return JWT token
@router.post("/login")
def login(credentials: LoginRequest):
    logger.info(f"🔐 POST /auth/login - Login attempt: {credentials.username}")
    try:
        if not dal_users.login_user(credentials.username, credentials.password):
            logger.warning(f"❌ POST /auth/login - Invalid credentials: {credentials.username}")
            raise HTTPException(status_code=401, detail="Invalid username or password")

        user = dal_users.get_user_by_username(credentials.username)
        
        if not user:
            logger.error(f"❌ POST /auth/login - User disappeared after login: {credentials.username}")
            raise HTTPException(status_code=500, detail="Authentication error")
        
        token = create_access_token(credentials.username)
        logger.info(f"✅ POST /auth/login - Login successful: {credentials.username}")
        return {"access_token": token, "token_type": "bearer", "user_name": user["user_name"], "id": user["id"]}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ POST /auth/login - Error: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Login error: {str(e)}")
