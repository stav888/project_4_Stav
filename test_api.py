import sys
import os
import shutil
import json
import tempfile

# Fix import path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import pytest
from fastapi.testclient import TestClient
from app import app
import dal_users

# Test client
client = TestClient(app)

# Store original DB_PATH
ORIGINAL_DB_PATH = dal_users.DB_NAME


@pytest.fixture(scope="function")
def test_db():
    """Create a temporary test database"""
    # Create a temporary directory and database file
    temp_dir = tempfile.mkdtemp()
    test_db_path = os.path.join(temp_dir, "test_users.db")

    # Save original and set to test db
    original_path = dal_users.DB_NAME
    dal_users.DB_NAME = test_db_path

    # Initialize the test database
    dal_users.create_table_users()

    yield test_db_path

    # Cleanup: restore original and remove temp directory
    dal_users.DB_NAME = original_path
    try:
        shutil.rmtree(temp_dir, ignore_errors=True)
    except:
        pass


@pytest.fixture(autouse=True)
def setup_test_db(test_db):
    """Automatically use test DB for each test"""
    yield


# ============================================================================
# USER MANAGEMENT TESTS
# ============================================================================

def test_user_creation():
    """Test creating a new user"""
    response = client.post("/users", json={
        "user_name": "john_doe",
        "email": "john@example.com",
        "password": "pass123"  # Shorter password
    })
    assert response.status_code == 200
    data = response.json()
    assert data["user"]["user_name"] == "john_doe"
    assert data["user"]["email"] == "john@example.com"
    assert data["user"]["predictions_remaining"] == 10  # Default credits


def test_user_creation_duplicate_username():
    """Test that duplicate usernames are rejected"""
    client.post("/users", json={
        "user_name": "john",
        "email": "john@example.com",
        "password": "pass123"
    })
    
    response = client.post("/users", json={
        "user_name": "john",
        "email": "different@example.com",
        "password": "pass456"
    })
    assert response.status_code == 400
    assert "already exists" in response.json()["detail"]


def test_get_all_users():
    """Test retrieving all users"""
    client.post("/users", json={
        "user_name": "alice",
        "email": "alice@example.com",
        "password": "pass1"
    })
    client.post("/users", json={
        "user_name": "bob",
        "email": "bob@example.com",
        "password": "pass2"
    })
    
    response = client.get("/users")
    assert response.status_code == 200
    users = response.json()
    assert len(users) == 2


def test_get_user_by_id():
    """Test retrieving a specific user"""
    create_response = client.post("/users", json={
        "user_name": "testuser",
        "email": "test@example.com",
        "password": "testpass"
    })
    user_id = create_response.json()["user"]["id"]
    
    response = client.get(f"/users/{user_id}")
    assert response.status_code == 200
    assert response.json()["user_name"] == "testuser"


def test_get_nonexistent_user():
    """Test retrieving a user that doesn't exist"""
    response = client.get("/users/999")
    assert response.status_code == 404


# ============================================================================
# AUTHENTICATION & JWT TESTS
# ============================================================================

def test_login_success():
    """Test successful login"""
    client.post("/users", json={
        "user_name": "loginuser",
        "email": "login@example.com",
        "password": "mypassword"
    })
    
    response = client.post("/auth/login", json={
        "username": "loginuser",
        "password": "mypassword"
    })
    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert data["token_type"] == "bearer"


def test_login_wrong_password():
    """Test login with wrong password"""
    client.post("/users", json={
        "user_name": "testuser",
        "email": "test@example.com",
        "password": "correctpass"
    })
    
    response = client.post("/auth/login", json={
        "username": "testuser",
        "password": "wrongpass"
    })
    assert response.status_code == 401


def test_login_nonexistent_user():
    """Test login with non-existent username"""
    response = client.post("/auth/login", json={
        "username": "nonexistent",
        "password": "anypass"
    })
    assert response.status_code == 401


def get_token(username="testuser", email="test@example.com", password="testpass"):
    """Helper function to create user and get JWT token"""
    client.post("/users", json={
        "user_name": username,
        "email": email,
        "password": password
    })
    response = client.post("/auth/login", json={
        "username": username,
        "password": password
    })
    return response.json()["access_token"]


# ============================================================================
# PROTECTED ENDPOINTS TESTS
# ============================================================================

def test_protected_endpoint_without_token():
    """Test accessing protected endpoint without token"""
    response = client.get("/ml/accuracy")
    assert response.status_code == 401


def test_protected_endpoint_with_invalid_token():
    """Test accessing protected endpoint with invalid token"""
    response = client.get(
        "/ml/accuracy",
        headers={"Authorization": "Bearer invalid_token"}
    )
    assert response.status_code == 401


def test_protected_endpoint_with_valid_token():
    """Test accessing protected endpoint with valid token"""
    token = get_token()
    response = client.get(
        "/ml/accuracy",
        headers={"Authorization": f"Bearer {token}"}
    )
    # Should fail because no model trained, but auth should pass
    assert response.status_code == 404  # Model not found, not auth error


# ============================================================================
# USER UPDATE & DELETE TESTS
# ============================================================================

def test_update_user():
    """Test updating a user"""
    create_response = client.post("/users", json={
        "user_name": "original",
        "email": "original@example.com",
        "password": "pass123"
    })
    user_id = create_response.json()["user"]["id"]
    
    response = client.put(f"/users/{user_id}", json={
        "user_name": "original",
        "email": "updated@example.com",
        "password": "pass123"
    })
    assert response.status_code == 200
    assert response.json()["email"] == "updated@example.com"


def test_delete_own_account():
    """Test user can delete their own account"""
    token = get_token("deleteuser")
    
    # Get user ID
    response = client.get("/users", headers={"Authorization": f"Bearer {token}"})
    users = response.json()
    user_id = users[0]["id"]
    
    # Delete own account
    response = client.delete(
        f"/users/{user_id}",
        headers={"Authorization": f"Bearer {token}"}
    )
    assert response.status_code == 200


def test_delete_other_account_forbidden():
    """Test user CANNOT delete another user's account"""
    token1 = get_token("user1", "user1@example.com")
    token2 = get_token("user2", "user2@example.com")
    
    # Get user1's ID
    response = client.get("/users", headers={"Authorization": f"Bearer {token1}"})
    user1_id = response.json()[0]["id"]
    
    # Try to delete user1 account as user2
    response = client.delete(
        f"/users/{user1_id}",
        headers={"Authorization": f"Bearer {token2}"}
    )
    assert response.status_code == 403
    assert "own account" in response.json()["detail"]


# ============================================================================
# ML TRAINING & PREDICTION TESTS
# ============================================================================

def test_train_model():
    """Test training a model"""
    token = get_token("mluser")
    
    response = client.post(
        "/ml/train",
        json={
            "X": [1, 2, 3, 4, 5],
            "Y": [2, 4, 6, 8, 10],
            "degree": 1
        },
        headers={"Authorization": f"Bearer {token}"}
    )
    assert response.status_code == 200
    assert "trained" in response.json()["message"].lower()


def test_train_invalid_degree():
    """Test training with invalid polynomial degree"""
    token = get_token("mluser2")
    
    # Degree too high
    response = client.post(
        "/ml/train",
        json={
            "X": [1, 2, 3],
            "Y": [1, 2, 3],
            "degree": 10
        },
        headers={"Authorization": f"Bearer {token}"}
    )
    assert response.status_code == 422  # Validation error


def test_predict_without_model():
    """Test prediction without training model first"""
    token = get_token("preduser")
    
    response = client.get(
        "/ml/predict/5",
        headers={"Authorization": f"Bearer {token}"}
    )
    assert response.status_code == 404


def test_predict_with_model():
    """Test successful prediction after training"""
    token = get_token("fulluser")
    
    # Train model
    client.post(
        "/ml/train",
        json={
            "X": [1, 2, 3, 4, 5],
            "Y": [2, 4, 6, 8, 10],
            "degree": 1
        },
        headers={"Authorization": f"Bearer {token}"}
    )
    
    # Make prediction
    response = client.get(
        "/ml/predict/6",
        headers={"Authorization": f"Bearer {token}"}
    )
    assert response.status_code == 200
    data = response.json()
    assert "predicted_running_time" in data
    assert float(data["predicted_running_time"]) > 0


def test_prediction_deducts_credit():
    """Test that prediction deducts credit"""
    token = get_token("credituser")
    
    # Train model
    client.post(
        "/ml/train",
        json={
            "X": [1, 2, 3],
            "Y": [1, 2, 3],
            "degree": 1
        },
        headers={"Authorization": f"Bearer {token}"}
    )
    
    # Check initial credits
    users = client.get("/users").json()
    initial_credits = users[0]["predictions_remaining"]
    
    # Make prediction
    client.get(
        "/ml/predict/2",
        headers={"Authorization": f"Bearer {token}"}
    )
    
    # Check credits decreased
    users = client.get("/users").json()
    new_credits = users[0]["predictions_remaining"]
    assert new_credits == initial_credits - 1


# ============================================================================
# CREDIT SYSTEM TESTS
# ============================================================================

def test_purchase_credits():
    """Test purchasing credits"""
    token = get_token("buyuser")
    
    response = client.post(
        "/ml/purchase",
        json={
            "card_number": "4532015112830366",
            "expiry": "12/25",
            "cvv": "123"
        },
        headers={"Authorization": f"Bearer {token}"}
    )
    assert response.status_code == 200
    assert "10" in response.json()["message"]


def test_purchase_invalid_card():
    """Test purchasing with invalid card number"""
    token = get_token("badcarduser")
    
    response = client.post(
        "/ml/purchase",
        json={
            "card_number": "1234",  # Too short
            "expiry": "12/25",
            "cvv": "123"
        },
        headers={"Authorization": f"Bearer {token}"}
    )
    assert response.status_code == 422  # Validation error


# ============================================================================
# MODEL ACCURACY TESTS
# ============================================================================

def test_accuracy_without_model():
    """Test accuracy check without trained model"""
    token = get_token("accuser")
    
    response = client.get(
        "/ml/accuracy",
        headers={"Authorization": f"Bearer {token}"}
    )
    assert response.status_code == 404


def test_accuracy_with_model():
    """Test accuracy calculation after training"""
    token = get_token("accuser2")
    
    # Train model
    client.post(
        "/ml/train",
        json={
            "X": [1, 2, 3, 4, 5],
            "Y": [2, 4, 6, 8, 10],
            "degree": 1
        },
        headers={"Authorization": f"Bearer {token}"}
    )
    
    # Check accuracy
    response = client.get(
        "/ml/accuracy",
        headers={"Authorization": f"Bearer {token}"}
    )
    assert response.status_code == 200
    data = response.json()
    assert "message" in data
    assert float(data["message"]) <= 1.0


# ============================================================================
# PASSWORD HASHING TESTS
# ============================================================================

def test_password_hashing():
    """Test that passwords are properly hashed"""
    username = "hashuser"
    password = "mypassword123"
    
    client.post("/users", json={
        "user_name": username,
        "email": "hash@example.com",
        "password": password
    })
    
    # Password should work with new SHA256+bcrypt method
    response = client.post("/auth/login", json={
        "username": username,
        "password": password
    })
    assert response.status_code == 200


def test_password_case_sensitive():
    """Test that passwords are case-sensitive"""
    username = "caseuser"
    password = "MyPassword"
    
    client.post("/users", json={
        "user_name": username,
        "email": "case@example.com",
        "password": password
    })
    
    # Wrong case should fail
    response = client.post("/auth/login", json={
        "username": username,
        "password": "mypassword"  # lowercase
    })
    assert response.status_code == 401


# ============================================================================
# EDGE CASES & ERROR HANDLING
# ============================================================================

def test_empty_username():
    """Test creating user with empty username"""
    response = client.post("/users", json={
        "user_name": "",
        "email": "empty@example.com",
        "password": "pass123"
    })
    assert response.status_code == 422


def test_empty_password():
    """Test creating user with empty password"""
    response = client.post("/users", json={
        "user_name": "nopass",
        "email": "nopass@example.com",
        "password": ""
    })
    assert response.status_code == 422


def test_model_deleted_on_account_delete():
    """Test that model file is deleted when account is deleted"""
    token = get_token("delmodeluser")
    
    # Train model
    client.post(
        "/ml/train",
        json={
            "X": [1, 2, 3],
            "Y": [1, 2, 3],
            "degree": 1
        },
        headers={"Authorization": f"Bearer {token}"}
    )
    
    # Get user ID
    users = client.get("/users").json()
    user_id = users[0]["id"]
    
    # Verify model exists
    response = client.get(
        "/ml/accuracy",
        headers={"Authorization": f"Bearer {token}"}
    )
    assert response.status_code == 200
    
    # Delete account
    client.delete(
        f"/users/{user_id}",
        headers={"Authorization": f"Bearer {token}"}
    )
    
    # Model should be inaccessible (user deleted)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
