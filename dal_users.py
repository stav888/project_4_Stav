"""
Data Access Layer - User Management
Handles all database operations for users.
"""

import sqlite3
import bcrypt
import logging
from typing import Optional, List, Dict, Any


DB_PATH = "users.db"


def init_db():
    """Initialize the SQLite database with users table."""
    conn = sqlite3.connect(DB_PATH, timeout=5.0)
    try:
        cursor = conn.cursor()
        
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_name TEXT UNIQUE NOT NULL,
            email TEXT NOT NULL,
            password TEXT NOT NULL,
            predictions_remaining INTEGER DEFAULT 10
        )
        """)
        
        conn.commit()
    finally:
        conn.close()


def hash_password(password: str) -> str:
    """
    Hash a password using bcrypt.

    Args:
        password (str): plaintext password

    Returns:
        str: hashed password
    """
    salt = bcrypt.gensalt()
    return bcrypt.hashpw(password.encode(), salt).decode()


def verify_password(password: str, hashed: str) -> bool:
    """
    Verify a plaintext password against a hash.

    Args:
        password (str): plaintext password
        hashed (str): hashed password

    Returns:
        bool: True if passwords match, False otherwise
    """
    return bcrypt.checkpw(password.encode(), hashed.encode())


def create_user(username: str, email: str, password: str) -> Optional[Dict[str, Any]]:
    """
    Create a new user in the database.

    Args:
        username (str): unique username
        email (str): user email
        password (str): plaintext password (will be hashed)

    Returns:
        dict: created user data, or None if failed
    """
    conn = None
    try:
        conn = sqlite3.connect(DB_PATH, timeout=5.0)
        cursor = conn.cursor()
        
        logging.debug(f"   🔄 Hashing password for user: {username}")
        hashed_pwd = hash_password(password)
        logging.debug(f"   ✓ Password hashed")
        
        logging.debug(f"   🔄 Inserting user record (username={username}, email={email})")
        cursor.execute("""
        INSERT INTO users (user_name, email, password, predictions_remaining)
        VALUES (?, ?, ?, 10)
        """, (username, email, hashed_pwd))
        
        conn.commit()
        user_id = cursor.lastrowid
        logging.debug(f"   ✓ User record inserted | New ID: {user_id}")
        logging.debug(f"   ✓ Default predictions allocated: 10")
        
        return {
            "id": user_id,
            "user_name": username,
            "email": email
        }
    except sqlite3.IntegrityError:
        logging.debug(f"   ✗ Username already exists: {username}")
        return None
    finally:
        if conn:
            conn.close()


def get_user_by_id(user_id: int) -> Optional[Dict[str, Any]]:
    """
    Get a user by ID.

    Args:
        user_id (int): user ID

    Returns:
        dict: user data (without password), or None if not found
    """
    conn = sqlite3.connect(DB_PATH, timeout=5.0)
    cursor = conn.cursor()
    
    cursor.execute("SELECT id, user_name, email, predictions_remaining FROM users WHERE id = ?", (user_id,))
    row = cursor.fetchone()
    conn.close()
    
    if row:
        return {
            "id": row[0],
            "user_name": row[1],
            "email": row[2],
            "predictions_remaining": row[3]
        }
    
    return None


def get_user_by_username(username: str) -> Optional[Dict[str, Any]]:
    """
    Get a user by username (for login).

    Args:
        username (str): username

    Returns:
        dict: user data including hashed password, or None if not found
    """
    conn = sqlite3.connect(DB_PATH, timeout=5.0)
    cursor = conn.cursor()
    
    cursor.execute("SELECT id, user_name, email, password, predictions_remaining FROM users WHERE user_name = ?", (username,))
    row = cursor.fetchone()
    conn.close()
    
    if row:
        return {
            "id": row[0],
            "user_name": row[1],
            "email": row[2],
            "password": row[3],
            "predictions_remaining": row[4]
        }
    
    return None


def get_all_users() -> List[Dict[str, Any]]:
    """
    Get all users from the database.

    Returns:
        list: list of user dictionaries (without passwords)
    """
    conn = sqlite3.connect(DB_PATH, timeout=5.0)
    cursor = conn.cursor()
    
    cursor.execute("SELECT id, user_name, email, predictions_remaining FROM users")
    rows = cursor.fetchall()
    conn.close()
    
    users = []
    for row in rows:
        users.append({
            "id": row[0],
            "user_name": row[1],
            "email": row[2],
            "predictions_remaining": row[3]
        })
    
    return users


def update_user(user_id: int, user_name: Optional[str] = None, email: Optional[str] = None, password: Optional[str] = None) -> Optional[Dict[str, Any]]:
    """
    Update a user's username, email and/or password.

    Args:
        user_id (int): user ID
        user_name (str): new username (optional)
        email (str): new email (optional)
        password (str): new plaintext password (optional)

    Returns:
        dict: updated user data, or None if failed
    """
    try:
        conn = sqlite3.connect(DB_PATH, timeout=5.0)
        try:
            cursor = conn.cursor()
            
            # Build dynamic update query
            updates = []
            params = []
            
            if user_name:
                updates.append("user_name = ?")
                params.append(user_name)
            if email:
                updates.append("email = ?")
                params.append(email)
            if password:
                hashed_pwd = hash_password(password)
                updates.append("password = ?")
                params.append(hashed_pwd)
            
            if not updates:
                return get_user_by_id(user_id)
            
            params.append(user_id)
            query = f"UPDATE users SET {', '.join(updates)} WHERE id = ?"
            cursor.execute(query, params)
            
            conn.commit()
            return get_user_by_id(user_id)
        finally:
            conn.close()
    except Exception as e:
        print(f"Error updating user: {e}")
        return None


def delete_user(user_id: int) -> bool:
    """
    Delete a user from the database and their model file.

    Args:
        user_id (int): user ID

    Returns:
        bool: True if successful, False otherwise
    """
    try:
        import os
        
        # First, get the username to find the .pkl file
        user = get_user_by_id(user_id)
        if not user:
            logging.warning(f"   ✗ Cannot delete - user not found: {user_id}")
            return False
        
        username = user['user_name']
        model_filename = f"{username}.pkl"
        
        # Delete the .pkl model file if it exists
        if os.path.exists(model_filename):
            try:
                os.remove(model_filename)
                logging.info(f"   ✓ Model file deleted: {model_filename}")
            except Exception as e:
                logging.warning(f"   ⚠️ Could not delete model file {model_filename}: {str(e)}")
        else:
            logging.debug(f"   ℹ️ No model file found: {model_filename}")
        
        # Delete from database
        conn = sqlite3.connect(DB_PATH, timeout=5.0)
        try:
            cursor = conn.cursor()
            
            logging.debug(f"   🔄 Removing user record from database...")
            cursor.execute("DELETE FROM users WHERE id = ?", (user_id,))
            conn.commit()
            logging.info(f"   ✓ Database record deleted")
        finally:
            conn.close()
        return True
    except Exception as e:
        logging.error(f"Error deleting user {user_id}: {str(e)}", exc_info=True)
        return False


def deduct_prediction(username: str) -> bool:
    """
    Deduct one prediction from a user's remaining count.

    Args:
        username (str): username

    Returns:
        bool: True if successful, False if no predictions left
    """
    user = get_user_by_username(username)
    
    if not user or user["predictions_remaining"] <= 0:
        logging.warning(f"🚫 DEDUCT PREDICTION BLOCKED - No credits remaining | Username: {username}")
        return False
    
    try:
        conn = sqlite3.connect(DB_PATH, timeout=5.0)
        try:
            cursor = conn.cursor()
            
            logging.debug(f"   🔄 Deducting 1 prediction credit from {username}")
            cursor.execute(
                "UPDATE users SET predictions_remaining = predictions_remaining - 1 WHERE user_name = ?",
                (username,)
            )
            
            conn.commit()
            new_count = user["predictions_remaining"] - 1
            logging.debug(f"   ✓ Prediction deducted | Remaining: {new_count}")
            return True
        finally:
            conn.close()
    except Exception as e:
        logging.error(f"Error deducting prediction: {e}")
        return False


def add_predictions(username: str, amount: int) -> Optional[int]:
    """
    Add predictions to a user's remaining count.

    Args:
        username (str): username
        amount (int): number of predictions to add

    Returns:
        int: new predictions remaining, or None if failed
    """
    try:
        conn = sqlite3.connect(DB_PATH, timeout=5.0)
        try:
            cursor = conn.cursor()
            
            logging.debug(f"   🔄 Adding {amount} predictions to {username}")
            cursor.execute(
                "UPDATE users SET predictions_remaining = predictions_remaining + ? WHERE user_name = ?",
                (amount, username)
            )
            
            conn.commit()
            
            # Get updated count
            cursor.execute("SELECT predictions_remaining FROM users WHERE user_name = ?", (username,))
            result = cursor.fetchone()
            
            if result:
                logging.debug(f"   ✓ Predictions added | New total: {result[0]}")
            return result[0] if result else None
        finally:
            conn.close()
    except Exception as e:
        logging.error(f"Error adding predictions: {e}")
        return None


def get_predictions_remaining(username: str) -> Optional[int]:
    """
    Get the number of predictions remaining for a user.

    Args:
        username (str): username

    Returns:
        int: predictions remaining, or None if user not found
    """
    user = get_user_by_username(username)
    return user["predictions_remaining"] if user else None
