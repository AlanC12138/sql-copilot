import uuid

from sqlalchemy import Engine, func, select

from app.models.tables import conversations, messages


def get_monthly_usage(engine: Engine, org_id: uuid.UUID) -> int:
    """Count user questions asked by this org since the start of the current calendar month (UTC)."""
    with engine.connect() as conn:
        count = conn.execute(
            select(func.count(messages.c.id))
            .select_from(messages.join(conversations, messages.c.conversation_id == conversations.c.id))
            .where(
                conversations.c.org_id == org_id,
                messages.c.role == "user",
                messages.c.created_at >= func.date_trunc("month", func.now()),
            )
        ).scalar_one()
    return count
