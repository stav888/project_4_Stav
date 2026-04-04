# 🏃‍♂️ Running Time Prediction API

A FastAPI-based REST API for predicting running times using polynomial regression, with JWT authentication, user management, and a credit-based prediction system.

---

## 📋 Overview

The system combines a Machine Learning model with a secured REST API, demonstrating a full end-to-end development process — from model training, through user management and JWT authentication, to running predictions via API calls.

Users can:
- Create accounts with secure password hashing
- Train polynomial regression models on their own data
- Make predictions based on training hours (credit system)
- Purchase additional prediction credits
- Manage their profile with full CRUD operations

---

## 🛠️ Tech Stack

| Component | Technology |
|---|---|
| Web Framework | FastAPI |
| Server | Uvicorn |
| Database | SQLite + sqlite3 |
| Authentication | PyJWT |
| Password Hashing | bcrypt (SHA256 + bcrypt) |
| ML Library | scikit-learn |
| Model Persistence | joblib |
| Environment | python-dotenv |

---

## 📦 Project Structure

```
project_4/
├── app.py              # FastAPI application entry point
├── auth.py             # JWT token generation and validation
├── dal_users.py        # Database access layer for user operations
├── main.py             # ML pipeline (train, predict, accuracy)
├── router_auth.py      # Authentication endpoints
├── router_ml.py        # ML training, prediction, purchase endpoints
├── router_users.py     # User CRUD endpoints
├── users.html          # User management frontend
├── ml.html             # ML operations frontend
├── requirements.txt    # Python dependencies
├── .env                # Environment variables (not in repo)
├── *.joblib            # Saved model file per user
└── README.md           # This file
```

---

## 🚀 Installation & Setup

### Prerequisites
- Python 3.8+
- pip

### Steps

**1. Clone the repository**
```bash
git clone https://github.com/stav888/project_4_Stav.git
cd project_4_Stav
```

**2. Install dependencies**
```bash
pip install -r requirements.txt
```

**3. Create `.env` file**
```
SECRET_KEY=your-secret-key-here
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=60
```

**4. Run the server**
```bash
uvicorn app:app --port 8000 --reload
```

**5. Access the application**
- Users page: http://127.0.0.1:8000/
- ML page: http://127.0.0.1:8000/ml
- Swagger UI: http://127.0.0.1:8000/docs

---

## 📖 API Endpoints

### 👤 User Endpoints

| Method | Endpoint | Description | Auth |
|---|---|---|---|
| `POST` | `/users` | Create new user | ❌ |
| `GET` | `/users` | Get all users | ❌ |
| `GET` | `/users/{id}` | Get user by ID | ❌ |
| `PUT` | `/users/{id}` | Update user | ✅ |
| `DELETE` | `/users/{id}` | Delete user | ✅ |

### 🔐 Auth Endpoints

| Method | Endpoint | Description | Auth |
|---|---|---|---|
| `POST` | `/auth/login` | Login and get JWT token | ❌ |

### 🤖 ML Endpoints

| Method | Endpoint | Description | Auth |
|---|---|---|---|
| `POST` | `/ml/train` | Train polynomial regression model | ✅ |
| `GET` | `/ml/predict/{hours}` | Predict running time | ✅ |
| `POST` | `/ml/purchase` | Purchase prediction credits | ✅ |
| `GET` | `/ml/accuracy` | Get model R² accuracy score | ✅ |
| `DELETE` | `/ml/model` | Delete trained model | ✅ |

---

## 📡 Usage Examples

### Create User
```bash
curl -X POST http://127.0.0.1:8000/users \
  -H "Content-Type: application/json" \
  -d '{"user_name": "john", "email": "john@example.com", "password": "pass1234"}'
```

### Login
```bash
curl -X POST http://127.0.0.1:8000/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username": "john", "password": "pass1234"}'
```
Returns:
```json
{
  "access_token": "eyJhbGci...",
  "token_type": "bearer",
  "user_name": "john",
  "id": 1
}
```

### Train Model
```bash
curl -X POST http://127.0.0.1:8000/ml/train \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{
    "X": [2, 3, 5, 7, 9, 12, 16, 20, 25, 30],
    "Y": [95, 85, 70, 65, 60, 55, 50, 53, 58, 70],
    "degree": 3
  }'
```

### Predict Running Time
```bash
curl -X GET http://127.0.0.1:8000/ml/predict/15 \
  -H "Authorization: Bearer <token>"
```
Returns:
```json
{
  "predicted_running_time": 52.4,
  "predictions_remaining": 9
}
```

### Purchase Credits
```bash
curl -X POST http://127.0.0.1:8000/ml/purchase \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{
    "card_number": "4532111111111111",
    "expiry": "12/27",
    "cvv": "123"
  }'
```
Returns:
```json
{
  "message": "Payment successful. 10 predictions added.",
  "predictions_remaining": 19
}
```

---

## 🗄️ Database Schema

```sql
CREATE TABLE users (
    id                    INTEGER PRIMARY KEY AUTOINCREMENT,
    user_name             TEXT NOT NULL UNIQUE,
    email                 TEXT NOT NULL UNIQUE,
    password              TEXT NOT NULL,
    predictions_remaining INTEGER DEFAULT 10
)
```

---

## 🎯 ML Model Details

- **Algorithm:** Polynomial Regression (scikit-learn Pipeline)
- **Default degree:** 3
- **Degree range:** 1–5 (validated by API)
- **Model file:** `<username>.joblib` — saved per user
- **Accuracy metric:** R² score

### Training Example (Python)
```python
from main import train_and_save_model, predict_from_model

training_hours = [2, 3, 5, 7, 9, 12, 16, 20, 25, 30]
running_times  = [95, 85, 70, 65, 60, 55, 50, 53, 58, 70]

train_and_save_model(training_hours, running_times, "john.joblib", degree=3)
result = predict_from_model("john.joblib", 15)
print(f"Predicted running time for 15 training hours: {result}")
```

---

## 💳 Credit System (Mega Bonus)

| Rule | Detail |
|---|---|
| New user | Gets **10** free predictions |
| Each `/ml/predict` call | Deducts **1** credit |
| Credits reach **0** | Predictions blocked → `403 Forbidden` |
| `POST /ml/purchase` | Adds **10** credits (simulated payment) |

---

## 🔐 Security

- Passwords stored using **SHA256 → bcrypt** double hashing
- JWT tokens expire after **60 minutes**
- All ML endpoints require valid Bearer token
- Users can only update/delete their own account
- Environment variables stored in `.env` (never committed)

---

## 📊 Logging

All operations are logged to `app.log` with emoji indicators:

```
🚀 Application startup
🔐 Login attempts
✅ Successful operations
❌ Errors and failures
🤖 Model training
🔮 Predictions
💳 Credit purchases
📊 Accuracy checks
🗑️ Deletions
```

---

## 📋 Submission

- **Course:** Data Science & Data Analyst 2025–2026
- **Project:** Project 4 — REST for ML
- **Email:** pythonai200425+project4restapi@gmail.com
- **GitHub:** https://github.com/stav888/project_4_Stav
