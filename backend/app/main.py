from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text

from app.db.app_engine import get_app_engine
from app.models.tables import metadata as app_metadata
from app.routers import billing, chat, connections

# Additive columns for tables that may already exist from an earlier phase.
# No Alembic yet at this stage of the project, so this stays a plain idempotent ALTER.
_ORGANIZATIONS_MIGRATIONS = [
    "ALTER TABLE organizations ADD COLUMN IF NOT EXISTS tier VARCHAR NOT NULL DEFAULT 'free'",
    "ALTER TABLE organizations ADD COLUMN IF NOT EXISTS stripe_customer_id VARCHAR",
    "ALTER TABLE organizations ADD COLUMN IF NOT EXISTS stripe_subscription_id VARCHAR",
    "ALTER TABLE organizations ADD COLUMN IF NOT EXISTS stripe_subscription_status VARCHAR",
]


@asynccontextmanager
async def lifespan(app: FastAPI):
    engine = get_app_engine()
    app_metadata.create_all(engine)
    with engine.begin() as conn:
        for stmt in _ORGANIZATIONS_MIGRATIONS:
            conn.execute(text(stmt))
    yield


app = FastAPI(title="SQL Copilot", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(chat.router)
app.include_router(connections.router)
app.include_router(billing.router)


@app.get("/health")
def health() -> dict:
    return {"status": "ok"}
