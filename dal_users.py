"""
Data Access Layer - User Management
Handles all database operations for users.
"""

import sqlite3
from passlib.context import CryptContext
import hashlib
import logging


DB_PATH = "users.db"
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


class Connection:
    """Context manager for database connections."""
    def __init__(self):
        self.conn = sqlite3.connect(DB_PATH, timeout=5.0)
        self.conn.row_factory = sqlite3.Row
    
    def __enter__(self):
        return self.conn
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.conn.close()


def get_connection():
    """Get a database connection context manager with timeout."""
    return Connection()


def row_to_dict(row):
    """Convert SQLite Row to dict, or return None."""
    return dict(row) if row else None


def init_db():
    """Initialize the SQLite database with users table."""
    with get_connection() as conn:
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


def hash_password(password):
    """
    Hash a password using SHA256 then bcrypt.

    Args:
        password (str): plaintext password

    Returns:
        str: hashed password
    """
    # Step 1: hash with SHA256 (no length limit)
    sha_password = hashlib.sha256(password.encode()).hexdigest()
    # Step 2: bcrypt the result
    return pwd_context.hash(sha_password)


def verify_password(password, hashed):
    """
    Verify a plaintext password against a hash.

    Args:
        password (str): plaintext password
        hashed (str): hashed password

    Returns:
        bool: True if passwords match, False otherwise
    """
    sha_password = hashlib.sha256(password.encode()).hexdigest()
    return pwd_context.verify(sha_password, hashed)


def create_user(username, email, password):
    """
    Create a new user in the database.

    Args:
        username (str): unique username
        email (str): user email
        password (str): plaintext password (will be hashed)

    Returns:
        dict: created user data, or None if failed
    """
    try:
        with get_connection() as conn:
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


def get_user_by_id(user_id):
    """
    Get a user by ID.

    Args:
        user_id (int): user ID

    Returns:
        dict: user data (without password), or None if not found
    """
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT id, user_name, email, predictions_remaining FROM users WHERE id = ?", (user_id,))
        row = cursor.fetchone()
        return row_to_dict(row)


def get_user_by_username(username):
    """
    Get a user by username (for login).

    Args:
        username (str): username

    Returns:
        dict: user data including hashed password, or None if not found
    """
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT id, user_name, email, password, predictions_remaining FROM users WHERE user_name = ?", (username,))
        row = cursor.fetchone()
        return row_to_dict(row)


def get_all_users():
    """
    Get all users from the database.

    Returns:
        list: list of user dictionaries (without passwords)
    """
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT id, user_name, email, predictions_remaining FROM users")
        return [row_to_dict(row) for row in cursor.fetchall()]


def update_user(user_id, user_name=None, email=None, password=None):
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
        with get_connection() as conn:
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
    except Exception as e:
        print(f"Error updating user: {e}")
        return None


def delete_user(user_id):
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
        with get_connection() as conn:
            cursor = conn.cursor()
            
            logging.debug(f"   🔄 Removing user record from database...")
            cursor.execute("DELETE FROM users WHERE id = ?", (user_id,))
            conn.commit()
            logging.info(f"   ✓ Database record deleted")
        return True
    except Exception as e:
        logging.error(f"Error deleting user {user_id}: {str(e)}", exc_info=True)
        return False


def deduct_prediction(username):
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
        with get_connection() as conn:
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
    except Exception as e:
        logging.error(f"Error deducting prediction: {e}")
        return False


def add_predictions(username, amount):
    """
    Add predictions to a user's remaining count.

    Args:
        username (str): username
        amount (int): number of predictions to add

    Returns:
        int: new predictions remaining, or None if failed
    """
    try:
        with get_connection() as conn:
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
    except Exception as e:
        logging.error(f"Error adding predictions: {e}")
        return None


def get_predictions_remaining(username):
    """
    Get the number of predictions remaining for a user.

    Args:
        username (str): username

    Returns:
        int: predictions remaining, or None if user not found
    """
    user = get_user_by_username(username)
    return user["predictions_remaining"] if user else None
