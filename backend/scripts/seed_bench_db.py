"""Seeds a deliberately noisy benchmark database for measuring schema-discovery cost.

The point of this database is to answer one question: does the agent's brute-force
schema discovery (`list_tables` then `get_schema`) still work when the target
database looks like a real warehouse instead of a tidy 4-table demo?

To keep the experiment controlled, the four real tables and their data are identical
to the demo dataset, so every gold query in eval/benchmark.json stays valid and the
only variable that changes is the surrounding noise. Two kinds of noise are added:

- Near-miss decoys: staging/dim/archive/v2 variants of the real tables. The nastiest
  ones share the real table's exact column names but hold only a subset of rows, so
  an agent that grabs `dim_customers` instead of `customers` returns a wrong count
  rather than an error — exactly the failure that's invisible without an eval.
- Warehouse noise: unrelated tables with realistic names and columns, to make
  `list_tables` output resemble a real warehouse's.

Usage:
    poetry run python scripts/seed_bench_db.py [--noise-tables 200]
"""
import argparse
import random
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from sqlalchemy import create_engine, text

from app.config import settings
from scripts.seed_demo_db import (
    build_dataset,
    customers,
    events,
    invoices,
    metadata,
    subscriptions,
)

random.seed(1337)

BENCH_DB = "sql_copilot_bench"

# Near-miss decoys keyed by the real table they shadow. `same_schema` variants are
# created with CREATE TABLE AS SELECT so they carry identical column names and a
# partial row set — the trap that produces a plausible but wrong answer.
SAME_SCHEMA_DECOYS = {
    "customers": [("dim_customers", 50), ("customers_archive", 80), ("customers_backup_2023", 120)],
    "subscriptions": [("dim_subscriptions", 40), ("subscriptions_archive", 90)],
    "invoices": [("fact_invoices", 300), ("invoices_archive", 500), ("invoices_2023", 200)],
    "events": [("fact_events", 250), ("events_archive", 400)],
}

# Renamed-column variants: a migration that half-happened, which is what makes
# picking the "obvious" table name risky in a real warehouse.
RENAMED_DECOYS = {
    "customers_v2": [
        "id INTEGER PRIMARY KEY", "full_name TEXT", "email_address TEXT",
        "region TEXT", "tier TEXT", "created_at TIMESTAMP",
    ],
    "stg_customers": [
        "id TEXT", "name TEXT", "email TEXT", "country TEXT", "plan TEXT", "signup_date TEXT",
    ],
    "subscriptions_v2": [
        "id INTEGER PRIMARY KEY", "account_id INTEGER", "tier TEXT",
        "state TEXT", "monthly_revenue_cents INTEGER", "activated_at TIMESTAMP",
    ],
    "stg_subscriptions": [
        "id TEXT", "customer_id TEXT", "plan TEXT", "status TEXT", "mrr_cents TEXT",
    ],
    "invoices_v2": [
        "id INTEGER PRIMARY KEY", "account_id INTEGER", "total_cents INTEGER",
        "payment_state TEXT", "created_at TIMESTAMP", "settled_at TIMESTAMP",
    ],
    "stg_invoices": [
        "id TEXT", "customer_id TEXT", "amount_cents TEXT", "status TEXT", "issued_at TEXT",
    ],
}

NOISE_DOMAINS = [
    "marketing", "support", "hr", "logistics", "finance", "product", "sales",
    "billing", "inventory", "shipping", "compliance", "security", "analytics",
    "partner", "vendor", "campaign", "survey", "referral", "payroll", "asset",
]
NOISE_ENTITIES = [
    "accounts", "records", "sessions", "tickets", "attempts", "batches", "jobs",
    "runs", "logs", "audits", "snapshots", "rollups", "mappings", "assignments",
    "reviews", "approvals", "channels", "segments", "budgets", "forecasts",
]
NOISE_PREFIXES = ["", "stg_", "dim_", "fact_", "raw_", "tmp_", "int_"]
NOISE_COLUMNS = [
    "id SERIAL PRIMARY KEY", "created_at TIMESTAMP", "updated_at TIMESTAMP",
    "status TEXT", "owner_id INTEGER", "external_ref TEXT", "notes TEXT",
    "amount_cents INTEGER", "quantity INTEGER", "is_active BOOLEAN",
    "source TEXT", "region TEXT", "category TEXT", "score NUMERIC",
]


def ensure_database() -> None:
    """CREATE DATABASE can't run inside a transaction, so use an AUTOCOMMIT connection."""
    admin_url = settings.demo_database_admin_url.rsplit("/", 1)[0] + "/postgres"
    engine = create_engine(admin_url, isolation_level="AUTOCOMMIT")
    with engine.connect() as conn:
        exists = conn.execute(
            text("SELECT 1 FROM pg_database WHERE datname = :n"), {"n": BENCH_DB}
        ).first()
        if not exists:
            conn.execute(text(f'CREATE DATABASE "{BENCH_DB}"'))
    engine.dispose()


def noise_table_names(count: int) -> list[str]:
    names: list[str] = []
    seen: set[str] = set()
    while len(names) < count:
        name = (
            f"{random.choice(NOISE_PREFIXES)}"
            f"{random.choice(NOISE_DOMAINS)}_{random.choice(NOISE_ENTITIES)}"
        )
        if name not in seen:
            seen.add(name)
            names.append(name)
    return names


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--noise-tables", type=int, default=200)
    args = parser.parse_args()

    ensure_database()

    bench_admin_url = settings.demo_database_admin_url.rsplit("/", 1)[0] + f"/{BENCH_DB}"
    engine = create_engine(bench_admin_url)

    with engine.begin() as conn:
        conn.execute(text("DROP SCHEMA public CASCADE"))
        conn.execute(text("CREATE SCHEMA public"))

        # 1. The real tables — identical schema and data to the demo dataset, so the
        #    existing gold SQL stays valid and only the noise around it changes.
        metadata.create_all(conn)
        customer_rows, subscription_rows, invoice_rows, event_rows = build_dataset()
        conn.execute(customers.insert(), customer_rows)
        conn.execute(subscriptions.insert(), subscription_rows)
        conn.execute(invoices.insert(), invoice_rows)
        conn.execute(events.insert(), event_rows)

        # 2. Same-schema decoys holding partial data.
        decoy_count = 0
        for real_table, variants in SAME_SCHEMA_DECOYS.items():
            for name, limit in variants:
                conn.execute(
                    text(f'CREATE TABLE "{name}" AS SELECT * FROM "{real_table}" LIMIT {limit}')
                )
                decoy_count += 1

        # 3. Renamed-column decoys (left empty — a half-finished migration).
        for name, columns in RENAMED_DECOYS.items():
            conn.execute(text(f'CREATE TABLE "{name}" ({", ".join(columns)})'))
            decoy_count += 1

        # 4. Unrelated warehouse noise.
        noise_names = noise_table_names(args.noise_tables)
        for name in noise_names:
            n_cols = random.randint(4, 9)
            cols = ["id SERIAL PRIMARY KEY"] + random.sample(NOISE_COLUMNS[1:], n_cols)
            conn.execute(text(f'CREATE TABLE "{name}" ({", ".join(cols)})'))

        # 5. The agent connects as the read-only role, so it needs access here too.
        role = "copilot_readonly"
        conn.execute(text(f"GRANT CONNECT ON DATABASE {BENCH_DB} TO {role}"))
        conn.execute(text(f"GRANT USAGE ON SCHEMA public TO {role}"))
        conn.execute(text(f"GRANT SELECT ON ALL TABLES IN SCHEMA public TO {role}"))
        conn.execute(
            text(f"ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT SELECT ON TABLES TO {role}")
        )

        total = conn.execute(
            text("SELECT count(*) FROM information_schema.tables WHERE table_schema = 'public'")
        ).scalar_one()

    engine.dispose()

    print(
        f"Seeded '{BENCH_DB}': {total} tables total "
        f"(4 real, {decoy_count} near-miss decoys, {len(noise_names)} noise)."
    )
    print(f"Real-table data matches the demo dataset, so eval/benchmark.json gold SQL still applies.")


if __name__ == "__main__":
    main()
