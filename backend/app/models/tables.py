import uuid

from sqlalchemy import Column, DateTime, ForeignKey, MetaData, String, Table, Text, func
from sqlalchemy.dialects.postgresql import UUID

metadata = MetaData()

organizations = Table(
    "organizations",
    metadata,
    Column("id", UUID(as_uuid=True), primary_key=True, default=uuid.uuid4),
    Column("clerk_org_id", String, unique=True, nullable=False),
    Column("name", String, nullable=False),
    Column("created_at", DateTime(timezone=True), server_default=func.now()),
    Column("tier", String, nullable=False, server_default="free"),
    Column("stripe_customer_id", String, nullable=True),
    Column("stripe_subscription_id", String, nullable=True),
    Column("stripe_subscription_status", String, nullable=True),
)

db_connections = Table(
    "db_connections",
    metadata,
    Column("id", UUID(as_uuid=True), primary_key=True, default=uuid.uuid4),
    Column("org_id", UUID(as_uuid=True), ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False),
    Column("name", String, nullable=False),
    Column("encrypted_url", Text, nullable=False),
    Column("created_at", DateTime(timezone=True), server_default=func.now()),
)

conversations = Table(
    "conversations",
    metadata,
    Column("id", UUID(as_uuid=True), primary_key=True, default=uuid.uuid4),
    Column("org_id", UUID(as_uuid=True), ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False),
    Column("clerk_user_id", String, nullable=False),
    Column("created_at", DateTime(timezone=True), server_default=func.now()),
)

messages = Table(
    "messages",
    metadata,
    Column("id", UUID(as_uuid=True), primary_key=True, default=uuid.uuid4),
    Column("conversation_id", UUID(as_uuid=True), ForeignKey("conversations.id", ondelete="CASCADE"), nullable=False),
    Column("role", String, nullable=False),
    Column("content", Text, nullable=False),
    Column("sql_query", Text, nullable=True),
    Column("created_at", DateTime(timezone=True), server_default=func.now()),
)
