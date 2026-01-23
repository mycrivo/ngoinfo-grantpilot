import os
from typing import Optional

from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker


DATABASE_URL = os.getenv("DATABASE_URL", "")

engine = create_engine(DATABASE_URL, pool_pre_ping=True) if DATABASE_URL else None
SessionLocal = (
    sessionmaker(bind=engine, autoflush=False, autocommit=False) if engine else None
)


def check_db_connection() -> Optional[str]:
    if not DATABASE_URL or engine is None:
        return "DATABASE_URL is not set"
    try:
        with engine.connect() as connection:
            connection.execute(text("SELECT 1"))
        return None
    except Exception as exc:  # pragma: no cover - used only for manual checks
        return f"DB connection failed: {exc}"
