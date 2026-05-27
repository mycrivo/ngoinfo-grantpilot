from fastapi import APIRouter

from app.reports.api.routes import health as health_routes

router = APIRouter()
router.include_router(health_routes.router)
