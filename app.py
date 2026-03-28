from fastapi import FastAPI
from fastapi.responses import FileResponse
import os
import logging

import dal_users
from router_users import router as users_router
from router_ml import router as ml_router

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('app.log', encoding='utf-8'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger('app')

app = FastAPI(title="🏃‍♂️ Running Time Prediction API")

@app.on_event("startup")
def startup():
    dal_users.init_db()
    logger.info("🚀 Application started - Database initialized")
    # Flush all handlers immediately after startup
    for handler in logging.getLogger().handlers:
        handler.flush()

@app.get("/")
def root():
    """Serve the users page"""
    if os.path.exists("users.html"):
        return FileResponse("users.html", media_type="text/html")
    return {"message": "🏃‍♂️ API Ready"}

@app.get("/ml")
def ml_page():
    """Serve ML page"""
    if os.path.exists("ml.html"):
        return FileResponse("ml.html", media_type="text/html")
    return {"message": "🏃‍♂️ ML Page"}

app.include_router(users_router)
app.include_router(ml_router)

# To run the app:
# uvicorn app:app --host 127.0.0.1 --port 8000 --reload
