import uuid

from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel
from sqlalchemy import select

from app.auth.clerk import Claims
from app.auth.crypto import decrypt, encrypt
from app.db.app_engine import get_app_engine
from app.models.tables import db_connections, organizations

router = APIRouter(prefix="/connections", tags=["connections"])


class ConnectionCreate(BaseModel):
    name: str
    database_url: str


class ConnectionOut(BaseModel):
    id: str
    name: str
    created_at: str


def _get_or_create_org(conn, clerk_org_id: str, name: str) -> uuid.UUID:
    row = conn.execute(
        select(organizations.c.id).where(organizations.c.clerk_org_id == clerk_org_id)
    ).first()
    if row:
        return row.id
    new_id = uuid.uuid4()
    conn.execute(organizations.insert().values(id=new_id, clerk_org_id=clerk_org_id, name=name))
    return new_id


@router.post("", response_model=ConnectionOut, status_code=status.HTTP_201_CREATED)
def create_connection(body: ConnectionCreate, claims: Claims):
    clerk_org_id = claims.get("org_id")
    if not clerk_org_id:
        raise HTTPException(status_code=400, detail="No active organization in session")

    engine = get_app_engine()
    with engine.begin() as conn:
        org_id = _get_or_create_org(conn, clerk_org_id, claims.get("org_slug", clerk_org_id))
        row_id = uuid.uuid4()
        conn.execute(db_connections.insert().values(
            id=row_id,
            org_id=org_id,
            name=body.name,
            encrypted_url=encrypt(body.database_url),
        ))
        row = conn.execute(
            select(db_connections).where(db_connections.c.id == row_id)
        ).first()

    return ConnectionOut(id=str(row.id), name=row.name, created_at=row.created_at.isoformat())


@router.get("", response_model=list[ConnectionOut])
def list_connections(claims: Claims):
    clerk_org_id = claims.get("org_id")
    if not clerk_org_id:
        return []

    engine = get_app_engine()
    with engine.connect() as conn:
        org_row = conn.execute(
            select(organizations.c.id).where(organizations.c.clerk_org_id == clerk_org_id)
        ).first()
        if not org_row:
            return []
        rows = conn.execute(
            select(db_connections).where(db_connections.c.org_id == org_row.id)
        ).fetchall()

    return [ConnectionOut(id=str(r.id), name=r.name, created_at=r.created_at.isoformat()) for r in rows]


@router.delete("/{connection_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_connection(connection_id: str, claims: Claims):
    clerk_org_id = claims.get("org_id")
    if not clerk_org_id:
        raise HTTPException(status_code=400, detail="No active organization in session")

    engine = get_app_engine()
    with engine.begin() as conn:
        org_row = conn.execute(
            select(organizations.c.id).where(organizations.c.clerk_org_id == clerk_org_id)
        ).first()
        if not org_row:
            raise HTTPException(status_code=404, detail="Connection not found")

        result = conn.execute(
            db_connections.delete().where(
                db_connections.c.id == uuid.UUID(connection_id),
                db_connections.c.org_id == org_row.id,
            )
        )
        if result.rowcount == 0:
            raise HTTPException(status_code=404, detail="Connection not found")
