"""
ML Model Endpoints
Handles model training and prediction with JWT authentication.
"""

from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel, Field
from typing import List, Optional
import logging
from auth import get_current_user
from main import train_and_save_model, predict_from_model
import dal_users
import os
import joblib
import numpy as np
from sklearn.metrics import r2_score

logger = logging.getLogger('app')
router = APIRouter(prefix="/ml", tags=["ml"])


class TrainRequest(BaseModel):
    """Request model for training."""
    X: List[float]
    Y: List[float]
    degree: int = Field(default=2, ge=1, le=5, description="Polynomial degree (1-5)")


class PredictResponse(BaseModel):
    """Response model for prediction."""
    predicted_running_time: float
    predictions_remaining: Optional[int] = None


class PurchaseRequest(BaseModel):
    """Request model for purchasing predictions."""
    card_number: str = Field(min_length=13, max_length=19)
    expiry: str
    cvv: str


def get_model_filename(username: str) -> str:
    """Generate model filename from username."""
    return f"{username}.joblib"


@router.post("/train")
def train_model(request: TrainRequest, current_user = Depends(get_current_user)):
    """Train a polynomial regression model."""
    username = current_user['user_name']
    logger.info(f"🤖 POST /train - Training model for {username} (degree={request.degree}, points={len(request.X)})")
    user = dal_users.get_user_by_username(username)
    if not user:
        logger.warning(f"❌ POST /train - User not found: {username}")
        raise HTTPException(status_code=404, detail="User not found. Account may have been deleted.")
    
    model_filename = get_model_filename(username)
    train_and_save_model(request.X, request.Y, model_filename, degree=request.degree)
    logger.info(f"✅ POST /train - Model trained for {username}")
    return {
        "message": f"Model trained and saved for user {username}",
        "model_name": model_filename,
        "degree": request.degree,
        "data_points": len(request.X)
    }


@router.delete("/model")
def delete_model(current_user = Depends(get_current_user)):
    """Delete user's trained model (called on logout)."""
    username = current_user['user_name']
    model_filename = get_model_filename(username)
    
    if os.path.exists(model_filename):
        try:
            os.remove(model_filename)
            logger.info(f"🗑️ DELETE /model - Model deleted for {username}")
            return {"message": "Model deleted"}
        except Exception as e:
            logger.error(f"❌ DELETE /model - Error deleting model for {username}: {str(e)}")
            raise HTTPException(status_code=500, detail=f"Error deleting model: {str(e)}")
    else:
        logger.info(f"ℹ️ DELETE /model - No model found for {username}")
        return {"message": "No model to delete"}


@router.get("/predict/{hours}")
def predict_running_time(hours: float, current_user = Depends(get_current_user)):
    """Predict running time for given training hours."""
    username = current_user['user_name']
    logger.info(f"🔮 GET /predict/{hours} - Predicting for {username}")
    user = dal_users.get_user_by_username(username)
    if not user:
        logger.warning(f"❌ GET /predict/{hours} - User not found: {username}")
        raise HTTPException(status_code=404, detail="User not found. Account may have been deleted.")
    
    model_filename = get_model_filename(username)
    if not os.path.exists(model_filename):
        logger.warning(f"❌ GET /predict/{hours} - Model not found for {username}")
        raise HTTPException(status_code=404, detail="Model not found. Please train a model first.")
    
    predictions_left = user.get("predictions_remaining")
    if predictions_left is not None and predictions_left <= 0:
        logger.warning(f"❌ GET /predict/{hours} - No predictions remaining for {username}")
        raise HTTPException(status_code=403, detail="No predictions remaining. Please purchase more credits.")
    
    try:
        prediction = predict_from_model(model_filename, hours)
    except Exception as e:
        logger.error(f"❌ GET /predict/{hours} - Prediction error for {username}: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Prediction error: {str(e)}")
    
    dal_users.deduct_prediction(username)
    predictions_remaining = dal_users.get_predictions_remaining(username)
    logger.info(f"✅ GET /predict/{hours} - Prediction successful for {username}: {prediction:.2f}")
    return {
        "predicted_running_time": round(prediction, 2),
        "predictions_remaining": predictions_remaining
    }


@router.post("/purchase")
def purchase_predictions(request: PurchaseRequest, current_user = Depends(get_current_user)):
    """Purchase additional predictions using credit card (simulated payment)."""
    username = current_user['user_name']
    logger.info(f"💳 POST /purchase - Purchase request from {username}")
    user = dal_users.get_user_by_username(username)
    if not user:
        logger.warning(f"❌ POST /purchase - User not found: {username}")
        raise HTTPException(status_code=404, detail="User not found. Account may have been deleted.")
    
    if not request.card_number or not request.expiry or not request.cvv:
        logger.warning(f"❌ POST /purchase - Invalid card details from {username}")
        raise HTTPException(status_code=400, detail="Invalid card details")
    card_number_str = str(request.card_number)
    if len(card_number_str) < 13 or len(card_number_str) > 19:
        raise HTTPException(status_code=400, detail="Invalid card number format (13-19 digits)")
    if not "/" in request.expiry or len(request.expiry) != 5:
        raise HTTPException(status_code=400, detail="Invalid expiry format (use MM/YY)")
    if len(request.cvv) != 3 or not request.cvv.isdigit():
        raise HTTPException(status_code=400, detail="Invalid CVV (must be exactly 3 digits)")
    
    new_count = dal_users.add_predictions(username, 10)
    logger.info(f"✅ POST /purchase - 10 predictions added for {username} (total: {new_count})")
    return {"message": "Payment successful. 10 predictions added.", "predictions_remaining": new_count}


@router.get("/accuracy")
def get_accuracy(current_user = Depends(get_current_user)):
    """Get R² accuracy score of the trained model."""
    username = current_user['user_name']
    logger.info(f"📊 GET /accuracy - Accuracy check for {username}")
    model_filename = get_model_filename(username)
    
    if not os.path.exists(model_filename):
        logger.warning(f"❌ GET /accuracy - Model not found for {username}")
        raise HTTPException(status_code=404, detail="Model not found. Please train a model first.")
    
    try:
        model = joblib.load(model_filename)
        # Test data - simple linear relationship
        X_test = np.array([[1], [2], [3], [4], [5], [6], [7], [8]])
        y_test = np.array([2, 4, 6, 8, 10, 12, 14, 16])
        y_pred = model.predict(X_test)
        r2 = float(r2_score(y_test, y_pred))
        logger.info(f"✅ GET /accuracy - R² Score: {r2:.4f} for {username}")
        return {"message": f"{r2:.4f}", "note": "R² Score (0.0-1.0, closer to 1.0 is better)"}
    except Exception as e:
        logger.error(f"❌ GET /accuracy - Error for {username}: {str(e)}")
        # Return error properly
        return {"message": "Error", "note": f"Could not calculate score: {str(e)}"}

