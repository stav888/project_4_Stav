from datetime import datetime, timedelta, timezone
from typing import Optional
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
import jwt
from jwt.exceptions import InvalidTokenError
import logging
import os
from dotenv import load_dotenv
import dal_users

# Load variables from .env into the environment
load_dotenv()

# Access the variables
SECRET_KEY = os.getenv("SECRET_KEY", "change-this-secret-key")  # Default fallback
ALGORITHM = os.getenv("ALGORITHM", "HS256")  # Default to HS256 if not set
# Convert to int since env variables are always strings
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "60"))

logger = logging.getLogger('app')

bearer_scheme = HTTPBearer()

def create_access_token(user_name: str) -> str:
    expire = datetime.now(timezone.utc) + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    payload = {
        "sub": user_name,
        "administrator": False,
        "exp": expire,
    }
    return jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)

def verify_token(token: str) -> Optional[str]:
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        user_name = payload.get("sub")
        return user_name if user_name else None
    except InvalidTokenError:
        return None

def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(bearer_scheme),
):
    token = credentials.credentials
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        user_name = payload.get("sub")
    except InvalidTokenError as exc:
        logger.warning(f"❌ Auth Error - Invalid or expired token")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
        ) from exc
    if not user_name:
        logger.warning(f"❌ Auth Error - Invalid token payload")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token payload",
        )
    user = dal_users.get_user_by_username(user_name)
    if user is None:
        logger.warning(f"❌ Auth Error - User does not exist: {user_name}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User does not exist",
        )
    logger.info(f"✅ Auth Success - User authenticated: {user_name}")
    return user
