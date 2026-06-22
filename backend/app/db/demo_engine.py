from functools import lru_cache

from sqlalchemy import create_engine
from sqlalchemy.engine import Engine

from app.config import settings


@lru_cache
def get_demo_engine() -> Engine:
    return create_engine(settings.demo_database_url, pool_pre_ping=True)
