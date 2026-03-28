"""
User Management Endpoints
Handles user CRUD operations and login.
"""

from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from typing import Optional
import logging
import dal_users
from auth import create_access_token, get_current_user

logger = logging.getLogger('app')
router = APIRouter(prefix="/users", tags=["users"])


class UserCreate(BaseModel):
    """Request model for creating a user."""
    user_name: str
    email: str
    password: str


class UserUpdate(BaseModel):
    """Request model for updating a user."""
    user_name: Optional[str] = None
    email: Optional[str] = None
    password: Optional[str] = None


class LoginRequest(BaseModel):
    """Request model for login."""
    username: str
    password: str


@router.post("")
def create_new_user(user: UserCreate):
    """Create a new user."""
    logger.info(f"📝 POST /users - Creating user: {user.user_name}")
    result = dal_users.create_user(user.user_name, user.email, user.password)
    if result is None:
        logger.warning(f"⚠️ POST /users - Username already exists: {user.user_name}")
        raise HTTPException(status_code=400, detail="Username already exists")
    logger.info(f"✅ POST /users - User created: {user.user_name}")
    return {"message": "User created successfully", "user": result}


@router.get("")
def get_users():
    """Get all users."""
    logger.info(f"📖 GET /users - Fetching all users")
    result = dal_users.get_all_users()
    logger.info(f"✅ GET /users - Retrieved {len(result)} users")
    return result


@router.get("/{user_id}")
def get_user(user_id: int):
    """Get a user by ID."""
    logger.info(f"📖 GET /users/{user_id} - Fetching user")
    user = dal_users.get_user_by_id(user_id)
    if user is None:
        logger.warning(f"⚠️ GET /users/{user_id} - User not found")
        raise HTTPException(status_code=404, detail="User not found")
    logger.info(f"✅ GET /users/{user_id} - User found: {user.get('user_name')}")
    return user


@router.put("/{user_id}")
def update_existing_user(user_id: int, user_data: UserUpdate):
    """Update a user."""
    logger.info(f"✏️ PUT /users/{user_id} - Updating user")
    result = dal_users.update_user(user_id, user_data.user_name, user_data.email, user_data.password)
    if result is None:
        logger.warning(f"⚠️ PUT /users/{user_id} - User not found")
        raise HTTPException(status_code=404, detail="User not found")
    logger.info(f"✅ PUT /users/{user_id} - User updated")
    return result


@router.delete("/{user_id}")
def delete_existing_user(user_id: int, current_user = Depends(get_current_user)):
    """Delete a user (requires authentication)."""
    logger.info(f"🗑️ DELETE /users/{user_id} - Deleting user by {current_user['user_name']}")
    user = dal_users.get_user_by_id(user_id)
    if user is None:
        logger.warning(f"⚠️ DELETE /users/{user_id} - User not found")
        raise HTTPException(status_code=404, detail="User not found")
    dal_users.delete_user(user_id)
    logger.info(f"✅ DELETE /users/{user_id} - User deleted")
    return {"message": f"User deleted successfully", "id": user_id}


@router.post("/auth/login")
def login(credentials: LoginRequest):
    """Login a user and return JWT token."""
    logger.info(f"🔐 POST /users/auth/login - Login attempt: {credentials.username}")
    user = dal_users.get_user_by_username(credentials.username)
    if user is None or not dal_users.verify_password(credentials.password, user["password"]):
        logger.warning(f"❌ POST /users/auth/login - Invalid credentials: {credentials.username}")
        raise HTTPException(status_code=401, detail="Invalid username or password")
    token = create_access_token(credentials.username)
    logger.info(f"✅ POST /users/auth/login - Login successful: {credentials.username}")
    return {"token": token, "user_name": user["user_name"], "id": user["id"]}
