import json
import uuid

from fastapi import APIRouter, HTTPException, status
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from sqlalchemy import create_engine, select

from app.agent.loop import run_agent, run_agent_stream
from app.auth.clerk import Claims
from app.auth.crypto import decrypt
from app.billing.usage import get_monthly_usage
from app.config import settings
from app.db.app_engine import get_app_engine
from app.db.demo_engine import get_demo_engine
from app.models.tables import conversations, db_connections, messages, organizations

router = APIRouter(tags=["chat"])

_TIER_LIMITS = {
    "free": (settings.free_tier_max_rows, settings.free_tier_statement_timeout_ms),
    "pro": (settings.pro_tier_max_rows, settings.pro_tier_statement_timeout_ms),
}

LIMIT_EXCEEDED_MESSAGE = (
    "You've used all of your free-tier questions for this month. "
    "Upgrade to Pro in Settings → Billing for unlimited questions."
)


class ChatRequest(BaseModel):
    question: str
    conversation_id: str | None = None


class ChatResponse(BaseModel):
    conversation_id: str
    answer: str
    sql: str | None = None
    columns: list[str] | None = None
    rows: list[list] | None = None
    truncated: bool = False
    failed: bool = False


def _resolve_engine(clerk_org_id: str | None):
    """Return (engine, org_id, tier). Falls back to the demo DB if org has no connection."""
    if not clerk_org_id:
        return get_demo_engine(), None, "free"

    app_engine = get_app_engine()
    with app_engine.connect() as conn:
        org_row = conn.execute(
            select(organizations.c.id, organizations.c.tier).where(organizations.c.clerk_org_id == clerk_org_id)
        ).first()
        if not org_row:
            return get_demo_engine(), None, "free"

        conn_row = conn.execute(
            select(db_connections.c.encrypted_url)
            .where(db_connections.c.org_id == org_row.id)
            .order_by(db_connections.c.created_at.desc())
            .limit(1)
        ).first()

    if conn_row:
        return create_engine(decrypt(conn_row.encrypted_url)), org_row.id, org_row.tier
    return get_demo_engine(), org_row.id, org_row.tier


def _over_free_tier_limit(org_id, tier: str) -> bool:
    if org_id is None or tier != "free":
        return False
    return get_monthly_usage(get_app_engine(), org_id) >= settings.free_tier_monthly_query_limit


def _persist(org_id: uuid.UUID, clerk_user_id: str, conv_id: str | None, question: str, answer: str, sql: str | None) -> str:
    app_engine = get_app_engine()
    with app_engine.begin() as conn:
        if conv_id:
            row = conn.execute(
                select(conversations.c.id).where(
                    conversations.c.id == uuid.UUID(conv_id),
                    conversations.c.org_id == org_id,
                )
            ).first()
            if not row:
                conv_id = None

        if not conv_id:
            new_id = uuid.uuid4()
            conn.execute(conversations.insert().values(
                id=new_id, org_id=org_id, clerk_user_id=clerk_user_id,
            ))
            conv_id = str(new_id)

        conn.execute(messages.insert().values(
            id=uuid.uuid4(), conversation_id=uuid.UUID(conv_id), role="user", content=question,
        ))
        conn.execute(messages.insert().values(
            id=uuid.uuid4(), conversation_id=uuid.UUID(conv_id),
            role="assistant", content=answer, sql_query=sql,
        ))

    return conv_id


@router.get("/chat/stream")
def chat_stream(question: str, claims: Claims, conversation_id: str | None = None):
    clerk_org_id = claims.get("org_id")
    clerk_user_id = claims.get("sub", "")
    engine, org_id, tier = _resolve_engine(clerk_org_id)

    def event_gen():
        if _over_free_tier_limit(org_id, tier):
            yield f"data: {json.dumps({'type': 'limit_exceeded', 'message': LIMIT_EXCEEDED_MESSAGE})}\n\n"
            yield "data: [DONE]\n\n"
            return

        max_rows, timeout_ms = _TIER_LIMITS[tier]
        answer_event: dict | None = None
        for event in run_agent_stream(question, engine=engine, max_rows=max_rows, timeout_ms=timeout_ms):
            yield f"data: {json.dumps(event, default=str)}\n\n"
            if event.get("type") == "answer":
                answer_event = event

        if org_id is not None and answer_event:
            _persist(
                org_id, clerk_user_id, conversation_id,
                question, answer_event.get("answer", ""), answer_event.get("sql"),
            )

        yield "data: [DONE]\n\n"

    return StreamingResponse(event_gen(), media_type="text/event-stream",
                             headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"})


@router.post("/chat", response_model=ChatResponse)
def chat(request: ChatRequest, claims: Claims):
    clerk_org_id = claims.get("org_id")
    clerk_user_id = claims.get("sub", "")

    engine, org_id, tier = _resolve_engine(clerk_org_id)
    if _over_free_tier_limit(org_id, tier):
        raise HTTPException(status_code=status.HTTP_402_PAYMENT_REQUIRED, detail=LIMIT_EXCEEDED_MESSAGE)

    max_rows, timeout_ms = _TIER_LIMITS[tier]
    result = run_agent(request.question, engine=engine, max_rows=max_rows, timeout_ms=timeout_ms)

    conv_id = None
    if org_id is not None:
        conv_id = _persist(org_id, clerk_user_id, request.conversation_id,
                           request.question, result.answer, result.sql)

    return ChatResponse(
        conversation_id=conv_id or "demo",
        answer=result.answer,
        sql=result.sql,
        columns=result.columns,
        rows=result.rows,
        truncated=result.truncated,
        failed=result.failed,
    )
