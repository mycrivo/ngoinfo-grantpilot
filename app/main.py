from fastapi import FastAPI

from app.api.routes.health import router as health_router
from app.core.config import validate_config

validate_config()

app = FastAPI()
app.include_router(health_router)
