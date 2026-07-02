from functools import lru_cache

from sqlalchemy import Engine, create_engine

from app.config import settings


@lru_cache
def get_app_engine() -> Engine:
    return create_engine(settings.app_database_url)
