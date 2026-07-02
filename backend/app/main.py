from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.db.app_engine import get_app_engine
from app.models.tables import metadata as app_metadata
from app.routers import chat, connections


@asynccontextmanager
async def lifespan(app: FastAPI):
    app_metadata.create_all(get_app_engine())
    yield


app = FastAPI(title="SQL Copilot", lifespan=lifespan)

app.include_router(chat.router)
app.include_router(connections.router)


@app.get("/health")
def health() -> dict:
    return {"status": "ok"}
