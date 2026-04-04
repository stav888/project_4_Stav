"""
User management endpoints - CRUD operations for users.
"""

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from typing import Optional
import logging

from auth import get_current_user
import dal_users


logger = logging.getLogger('app')
router = APIRouter(prefix="/users", tags=["users"])


# Request model for creating a user
class UserCreate(BaseModel):
    user_name: str = Field(..., min_length=1, max_length=50)
    email: str
    password: str = Field(..., min_length=4, max_length=100)


# Request model for updating a user
class UserUpdate(BaseModel):
    user_name: Optional[str] = None
    email: Optional[str] = None
    password: Optional[str] = None


# Create new user endpoint
@router.post("")
def create_new_user(user: UserCreate):
    logger.info(f"📝 POST /users - Creating user: {user.user_name}")
    result = dal_users.insert_user(user.user_name, user.email, user.password)

    if result is None:
        logger.warning(f"⚠️ POST /users - Username already exists: {user.user_name}")
        raise HTTPException(status_code=400, detail="Username already exists")

    logger.info(f"✅ POST /users - User created: {user.user_name}")
    return {"message": "User created successfully", "user": result}


# Get all users endpoint
@router.get("")
def get_users():
    logger.info(f"📖 GET /users - Fetching all users")
    result = dal_users.get_all_users()
    logger.info(f"✅ GET /users - Retrieved {len(result)} users")
    return result


# Get user by ID endpoint
@router.get("/{user_id}")
def get_user(user_id: int):
    logger.info(f"📖 GET /users/{user_id} - Fetching user")
    user = dal_users.get_user_by_id(user_id)
    if user is None:
        logger.warning(f"⚠️ GET /users/{user_id} - User not found")
        raise HTTPException(status_code=404, detail="User not found")
    logger.info(f"✅ GET /users/{user_id} - User found: {user.get('user_name')}")
    return user


# Update user endpoint (requires authentication)
@router.put("/{user_id}")
def update_existing_user(user_id: int, user_data: UserUpdate, current_user=Depends(get_current_user)):
    if current_user["id"] != user_id:
        logger.warning(f"⚠️ PUT /users/{user_id} - Unauthorized update attempt by {current_user['user_name']}")
        raise HTTPException(status_code=403, detail="Can only update own account")
    
    logger.info(f"✏️ PUT /users/{user_id} - Updating user by {current_user['user_name']}")
    current = dal_users.get_user_by_id(user_id)
    if current is None:
        logger.warning(f"⚠️ PUT /users/{user_id} - User not found")
        raise HTTPException(status_code=404, detail="User not found")

    new_username = user_data.user_name or current["user_name"]
    new_email = user_data.email or current["email"]
    new_password = user_data.password if user_data.password else None

    result = dal_users.update_user(user_id, new_username, new_email, new_password)

    if result is None:
        logger.warning(f"⚠️ PUT /users/{user_id} - Update failed")
        raise HTTPException(status_code=404, detail="User not found")
    if result == "duplicate":
        raise HTTPException(status_code=400, detail="Username or email already exists")

    logger.info(f"✅ PUT /users/{user_id} - User updated")
    return {"message": "User updated successfully", "user": result}


# Delete user endpoint (requires authentication)
@router.delete("/{user_id}")
def delete_existing_user(user_id: int, current_user=Depends(get_current_user)):
    if current_user["id"] != user_id:
        logger.warning(f"⚠️ DELETE /users/{user_id} - Unauthorized delete attempt by {current_user['user_name']}")
        raise HTTPException(status_code=403, detail="Can only delete own account")

    logger.info(f"🗑️ DELETE /users/{user_id} - Deleting user by {current_user['user_name']}")
    deleted = dal_users.delete_user(user_id)
    if deleted is None:
        logger.warning(f"⚠️ DELETE /users/{user_id} - User not found")
        raise HTTPException(status_code=404, detail="User not found")

    logger.info(f"✅ DELETE /users/{user_id} - User deleted")
    return {"message": "User deleted successfully", "user": deleted}


# Recreate users table (requires authentication)
@router.delete("/table/recreate")
def recreate_users_table(current_user=Depends(get_current_user)):
    logger.info(f"🔄 DELETE /table/recreate - Recreating users table by {current_user['user_name']}")
    dal_users.recreate_table_users()
    logger.info(f"✅ DELETE /table/recreate - Users table recreated")
    return {"message": "Users table dropped and recreated successfully"}
