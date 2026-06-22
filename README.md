# SQL Copilot

Multi-tenant SaaS where a user connects a database and asks questions in plain English. An agent explores the schema, writes SQL through a read-only sandbox, self-corrects on errors, and returns a table + chart — with a fixed eval suite tracking accuracy and Stripe usage-based billing metering every query.

## Why this exists

Self-serve analytics without writing SQL is a real, fundable product category (Snowflake Cortex Analyst, Databricks Genie, Hex Magic). This project demonstrates the parts that matter for *production* AI engineering, not just a single LLM call:

- Agentic tool-use loop (plan → call tool → observe → self-correct)
- A safety sandbox around LLM-generated SQL (read-only role, statement allow-list, cost guard, timeout, row cap)
- A quantifiable eval harness (NL→SQL benchmark, exact-match / execution-match accuracy)
- Multi-tenant auth, usage-based billing, and LLM observability — the SaaS plumbing most AI portfolios skip

See [MVP.md](MVP.md) for scope/phases and [TECH_STACK.md](TECH_STACK.md) for stack decisions and rationale.

## Status

Phase 1 (core agent) in progress. No auth/billing/frontend yet — see MVP.md for the phase plan.

## Local development

```bash
docker compose up -d postgres
cd backend
poetry install
poetry run python scripts/seed_demo_db.py
poetry run uvicorn app.main:app --reload
```

Then `POST http://localhost:8000/chat` with `{"question": "..."}`.
