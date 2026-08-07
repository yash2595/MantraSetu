from fastapi import APIRouter, Depends
from app.core.config import Settings, settings

router = APIRouter()

def get_settings():
    return settings

@router.get("/health", summary="Health Check")
def health(config: Settings = Depends(get_settings)):
    return {
        "status": "Healthy",
        "app_name": config.APP_NAME,
        "version": config.APP_VERSION
    }