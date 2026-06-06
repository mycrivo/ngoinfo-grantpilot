from fastapi import APIRouter, Depends

from app.reports.api.dependencies.plan_gate import require_impact_plan
from app.reports.api.routes import read as read_routes
from app.reports.api.routes import export as export_routes
from app.reports.api.routes import gate1 as gate1_routes
from app.reports.api.routes import gate2 as gate2_routes
from app.reports.api.routes import gate3 as gate3_routes
from app.reports.api.routes import health as health_routes
from app.reports.api.routes import lifecycle as lifecycle_routes

router = APIRouter()
router.include_router(health_routes.router)

gated_router = APIRouter(dependencies=[Depends(require_impact_plan)])
gated_router.include_router(read_routes.router)
gated_router.include_router(lifecycle_routes.router)
gated_router.include_router(export_routes.router)
gated_router.include_router(gate1_routes.router)
gated_router.include_router(gate2_routes.router)
gated_router.include_router(gate3_routes.router)
router.include_router(gated_router)
