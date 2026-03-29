"""
User Management Endpoints
Handles user CRUD operations and login.
"""

from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from typing import Optional
import logging
import dal_users
from auth import get_current_user

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


@router.post("")
def create_new_user(user: UserCreate):
    """Create a new user."""
    logger.info(f"📝 POST /users - Creating user: {user.user_name}")
    try:
        result = dal_users.create_user(user.user_name, user.email, user.password)
        if result is None:
            logger.warning(f"⚠️ POST /users - Username already exists: {user.user_name}")
            raise HTTPException(status_code=400, detail="Username already exists")
        logger.info(f"✅ POST /users - User created: {user.user_name}")
        return {"message": "User created successfully", "user": result}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ POST /users - Error creating user: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error creating user: {str(e)}")


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
    if current_user["id"] != user_id:
        logger.warning(f"⚠️ DELETE /users/{user_id} - Unauthorized delete attempt by {current_user['user_name']}")
        raise HTTPException(status_code=403, detail="Can only delete own account")
    logger.info(f"🗑️ DELETE /users/{user_id} - Deleting user by {current_user['user_name']}")
    user = dal_users.get_user_by_id(user_id)
    if user is None:
        logger.warning(f"⚠️ DELETE /users/{user_id} - User not found")
        raise HTTPException(status_code=404, detail="User not found")
    dal_users.delete_user(user_id)
    logger.info(f"✅ DELETE /users/{user_id} - User deleted")
    return {"message": f"User deleted successfully", "id": user_id}
