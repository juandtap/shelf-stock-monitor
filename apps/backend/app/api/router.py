from fastapi import APIRouter

from app.api.routes.cameras import router as cameras_router
from app.api.routes.products import router as products_router
from app.api.routes.shelf_configurations import (
    router as shelf_configurations_router,
)
from app.api.routes.stock_alerts import router as stock_alerts_router
from app.api.routes.stock_observations import (
    router as stock_observations_router,
)

api_router = APIRouter()

api_router.include_router(cameras_router)
api_router.include_router(products_router)
api_router.include_router(stock_observations_router)
api_router.include_router(shelf_configurations_router)
api_router.include_router(stock_alerts_router)
