from fastapi import APIRouter

from app.reports.api.routes import gate1 as gate1_routes
from app.reports.api.routes import gate2 as gate2_routes
from app.reports.api.routes import health as health_routes
from app.reports.api.routes import lifecycle as lifecycle_routes

router = APIRouter()
router.include_router(health_routes.router)
router.include_router(lifecycle_routes.router)
router.include_router(gate1_routes.router)
router.include_router(gate2_routes.router)
