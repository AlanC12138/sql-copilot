"""Seeds the demo SaaS-metrics dataset and creates the read-only role the agent executes as."""
import random
import sys
from datetime import datetime, timedelta
from pathlib import Path

# Allow running as `python scripts/seed_demo_db.py` from backend/ without installing the package.
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from faker import Faker
from sqlalchemy import (
    Column, Date, DateTime, ForeignKey, Integer, MetaData, String, Table, create_engine, text,
)
from sqlalchemy.dialects.postgresql import JSONB

from app.config import settings

fake = Faker()
random.seed(42)
Faker.seed(42)

metadata = MetaData()

customers = Table(
    "customers", metadata,
    Column("id", Integer, primary_key=True),
    Column("name", String, nullable=False),
    Column("email", String, nullable=False, unique=True),
    Column("country", String, nullable=False),
    Column("plan", String, nullable=False),
    Column("signup_date", Date, nullable=False),
)

subscriptions = Table(
    "subscriptions", metadata,
    Column("id", Integer, primary_key=True),
    Column("customer_id", Integer, ForeignKey("customers.id"), nullable=False),
    Column("plan", String, nullable=False),
    Column("status", String, nullable=False),
    Column("mrr_cents", Integer, nullable=False),
    Column("started_at", DateTime, nullable=False),
    Column("canceled_at", DateTime, nullable=True),
)

invoices = Table(
    "invoices", metadata,
    Column("id", Integer, primary_key=True),
    Column("customer_id", Integer, ForeignKey("customers.id"), nullable=False),
    Column("subscription_id", Integer, ForeignKey("subscriptions.id"), nullable=True),
    Column("amount_cents", Integer, nullable=False),
    Column("status", String, nullable=False),
    Column("issued_at", DateTime, nullable=False),
    Column("paid_at", DateTime, nullable=True),
)

events = Table(
    "events", metadata,
    Column("id", Integer, primary_key=True),
    Column("customer_id", Integer, ForeignKey("customers.id"), nullable=False),
    Column("event_type", String, nullable=False),
    Column("occurred_at", DateTime, nullable=False),
    Column("metadata", JSONB, nullable=True),
)

PLANS = {"free": 0, "starter": 2900, "pro": 9900, "enterprise": 49900}
EVENT_TYPES = ["login", "feature_used", "support_ticket", "upgrade_viewed", "churn_risk_flag"]


def build_dataset(n_customers=200):
    customer_rows, subscription_rows, invoice_rows, event_rows = [], [], [], []
    sub_id = invoice_id = event_id = 1

    for cid in range(1, n_customers + 1):
        plan = random.choices(list(PLANS), weights=[15, 35, 35, 15])[0]
        signup = fake.date_between(start_date="-2y", end_date="-1m")
        customer_rows.append({
            "id": cid, "name": fake.name(), "email": fake.unique.email(),
            "country": fake.country(), "plan": plan, "signup_date": signup,
        })

        started_at = datetime.combine(signup, datetime.min.time())
        is_canceled = random.random() < 0.2
        canceled_at = started_at + timedelta(days=random.randint(30, 500)) if is_canceled else None
        subscription_rows.append({
            "id": sub_id, "customer_id": cid, "plan": plan,
            "status": "canceled" if is_canceled else "active",
            "mrr_cents": PLANS[plan], "started_at": started_at, "canceled_at": canceled_at,
        })
        this_sub_id, sub_id = sub_id, sub_id + 1

        end = canceled_at or datetime.utcnow()
        cursor = started_at
        while cursor < end and PLANS[plan] > 0:
            paid = random.random() > 0.05
            invoice_rows.append({
                "id": invoice_id, "customer_id": cid, "subscription_id": this_sub_id,
                "amount_cents": PLANS[plan], "status": "paid" if paid else "failed",
                "issued_at": cursor, "paid_at": cursor + timedelta(days=1) if paid else None,
            })
            invoice_id += 1
            cursor += timedelta(days=30)

        for _ in range(random.randint(2, 12)):
            occurred = started_at + timedelta(days=random.randint(0, max((end - started_at).days, 1)))
            event_rows.append({
                "id": event_id, "customer_id": cid, "event_type": random.choice(EVENT_TYPES),
                "occurred_at": occurred, "metadata": {"source": random.choice(["web", "mobile", "api"])},
            })
            event_id += 1

    return customer_rows, subscription_rows, invoice_rows, event_rows


def ensure_readonly_role(conn, role="copilot_readonly", password="copilot_readonly"):
    # Role/password here are fixed internal constants, not external input, so direct
    # interpolation into DDL is fine — Postgres DDL doesn't reliably accept bind params
    # for identifiers or PASSWORD literals.
    exists = conn.execute(text("SELECT 1 FROM pg_roles WHERE rolname = :role"), {"role": role}).first()
    if not exists:
        conn.execute(text(f"CREATE ROLE {role} LOGIN PASSWORD '{password}'"))
    conn.execute(text(f"GRANT CONNECT ON DATABASE sql_copilot_demo TO {role}"))
    conn.execute(text(f"GRANT USAGE ON SCHEMA public TO {role}"))
    conn.execute(text(f"GRANT SELECT ON ALL TABLES IN SCHEMA public TO {role}"))
    conn.execute(text(f"ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT SELECT ON TABLES TO {role}"))


def main():
    engine = create_engine(settings.demo_database_admin_url)
    with engine.begin() as conn:
        metadata.drop_all(conn)
        metadata.create_all(conn)

        customer_rows, subscription_rows, invoice_rows, event_rows = build_dataset()
        conn.execute(customers.insert(), customer_rows)
        conn.execute(subscriptions.insert(), subscription_rows)
        conn.execute(invoices.insert(), invoice_rows)
        conn.execute(events.insert(), event_rows)

        ensure_readonly_role(conn)

    print(
        f"Seeded {len(customer_rows)} customers, {len(subscription_rows)} subscriptions, "
        f"{len(invoice_rows)} invoices, {len(event_rows)} events."
    )
    print("Read-only role 'copilot_readonly' ready.")


if __name__ == "__main__":
    main()
