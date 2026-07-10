import uuid

from sqlalchemy import select

from app.models.tables import organizations


def get_or_create_org(conn, clerk_org_id: str, name: str) -> uuid.UUID:
    row = conn.execute(
        select(organizations.c.id).where(organizations.c.clerk_org_id == clerk_org_id)
    ).first()
    if row:
        return row.id
    new_id = uuid.uuid4()
    conn.execute(organizations.insert().values(id=new_id, clerk_org_id=clerk_org_id, name=name))
    return new_id
