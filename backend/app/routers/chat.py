import json
import uuid

from fastapi import APIRouter, HTTPException, status
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from sqlalchemy import case, create_engine, select

from app.agent.loop import run_agent, run_agent_stream
from app.auth.clerk import Claims
from app.auth.crypto import decrypt
from app.billing.usage import get_monthly_usage
from app.config import settings
from app.db.app_engine import get_app_engine
from app.db.demo_engine import get_demo_engine
from app.models.org import get_or_create_org
from app.models.tables import conversations, db_connections, messages, organizations

router = APIRouter(tags=["chat"])

# Cap replayed context so a long conversation can't grow the prompt without bound.
HISTORY_MAX_MESSAGES = 20

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


def _resolve_engine(clerk_org_id: str | None, org_name: str = ""):
    """Return (engine, org_id, tier). Falls back to the demo DB if org has no connection."""
    if not clerk_org_id:
        return get_demo_engine(), None, "free"

    app_engine = get_app_engine()
    with app_engine.begin() as conn:
        # Create on first contact: otherwise a user who chats before ever opening
        # settings/billing has no org row, so nothing they say gets persisted.
        org_id = get_or_create_org(conn, clerk_org_id, org_name or clerk_org_id)
        tier = conn.execute(
            select(organizations.c.tier).where(organizations.c.id == org_id)
        ).scalar_one()

        conn_row = conn.execute(
            select(db_connections.c.encrypted_url)
            .where(db_connections.c.org_id == org_id)
            .order_by(db_connections.c.created_at.desc())
            .limit(1)
        ).first()

    if conn_row:
        return create_engine(decrypt(conn_row.encrypted_url)), org_id, tier
    return get_demo_engine(), org_id, tier


def _load_history(org_id, conv_id: str | None) -> list[dict]:
    """Prior turns of this conversation, oldest first, capped to the most recent N."""
    if org_id is None or not conv_id:
        return []
    try:
        conv_uuid = uuid.UUID(conv_id)
    except ValueError:
        return []

    # Both messages of a turn are inserted in one transaction, and Postgres `now()`
    # is the transaction timestamp — so their created_at values are identical.
    # Rank on role to keep the question ahead of its answer.
    role_rank = case((messages.c.role == "user", 0), else_=1)

    with get_app_engine().connect() as conn:
        rows = conn.execute(
            select(messages.c.role, messages.c.content)
            .select_from(
                messages.join(conversations, messages.c.conversation_id == conversations.c.id)
            )
            .where(conversations.c.id == conv_uuid, conversations.c.org_id == org_id)
            .order_by(messages.c.created_at, role_rank)
        ).fetchall()

    return [{"role": r.role, "content": r.content} for r in rows][-HISTORY_MAX_MESSAGES:]


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
    engine, org_id, tier = _resolve_engine(clerk_org_id, claims.get("org_slug", ""))
    history = _load_history(org_id, conversation_id)

    def event_gen():
        if _over_free_tier_limit(org_id, tier):
            yield f"data: {json.dumps({'type': 'limit_exceeded', 'message': LIMIT_EXCEEDED_MESSAGE})}\n\n"
            yield "data: [DONE]\n\n"
            return

        max_rows, timeout_ms = _TIER_LIMITS[tier]
        answer_event: dict | None = None
        for event in run_agent_stream(
            question, engine=engine, max_rows=max_rows, timeout_ms=timeout_ms, history=history
        ):
            yield f"data: {json.dumps(event, default=str)}\n\n"
            if event.get("type") == "answer":
                answer_event = event

        if org_id is not None and answer_event:
            conv_id = _persist(
                org_id, clerk_user_id, conversation_id,
                question, answer_event.get("answer", ""), answer_event.get("sql"),
            )
            # The client needs this to send the next question into the same thread.
            yield f"data: {json.dumps({'type': 'conversation', 'conversation_id': conv_id})}\n\n"

        yield "data: [DONE]\n\n"

    return StreamingResponse(event_gen(), media_type="text/event-stream",
                             headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"})


@router.post("/chat", response_model=ChatResponse)
def chat(request: ChatRequest, claims: Claims):
    clerk_org_id = claims.get("org_id")
    clerk_user_id = claims.get("sub", "")

    engine, org_id, tier = _resolve_engine(clerk_org_id, claims.get("org_slug", ""))
    if _over_free_tier_limit(org_id, tier):
        raise HTTPException(status_code=status.HTTP_402_PAYMENT_REQUIRED, detail=LIMIT_EXCEEDED_MESSAGE)

    history = _load_history(org_id, request.conversation_id)
    max_rows, timeout_ms = _TIER_LIMITS[tier]
    result = run_agent(
        request.question, engine=engine, max_rows=max_rows, timeout_ms=timeout_ms, history=history
    )

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
