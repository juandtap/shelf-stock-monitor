from fastapi import APIRouter

from app.api.routes.cameras import router as cameras_router

api_router = APIRouter()

api_router.include_router(cameras_router)
