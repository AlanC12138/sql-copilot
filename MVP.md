# SQL Copilot — MVP & Phase Plan

## Pitch

A multi-tenant SaaS where users connect a database and ask questions in plain English. The agent explores the schema, writes SQL through a read-only sandbox, self-corrects on errors, and returns a table + chart — with a 50-question eval suite tracking accuracy and Stripe usage-based billing metering every query.

## Core user flow (target)

1. User signs up, creates a workspace (org), connects a database (or uses the bundled demo dataset).
2. User asks a question in chat: *"Which customers churned last quarter and what was their MRR?"*
3. Agent retrieves relevant schema context, calls `list_tables` / `get_schema` / `run_sql` as needed, self-corrects once on a SQL error.
4. Response streams back: natural-language summary, the SQL it ran (shown for transparency), a result table, and an auto-picked chart.
5. Usage is metered; free tier caps at N queries/month, Pro tier is unlimited with higher row/timeout limits.

## Demo dataset

A synthetic SaaS-metrics schema: `customers`, `subscriptions`, `invoices`, `events`. Realistic enough to require multi-table joins (e.g., "MRR by plan for customers signed up in Q1") without needing a real customer's data.

## Phases

| Phase | Scope | Notes |
|---|---|---|
| **1 — Core agent** (current) | Tool-use loop, SQL sandbox, single hardcoded demo DB, no auth, tested via CLI/Postman | No persistence beyond the demo DB; no streaming yet |
| 2 — Eval harness | Fixed 50-question NL→SQL benchmark against the demo schema; exact-match + execution-match accuracy, run via `make eval` | The number you can quote — also the regression guard for prompt changes |
| 3 — Multi-tenant + auth | Clerk integration, orgs, per-tenant DB connections, encrypted credentials at rest | App database (orgs/users/connections/conversations) introduced here, not before |
| 4 — Frontend | Next.js (App Router): SSR marketing/pricing pages + authenticated app shell + streaming chat (SSE), table/chart rendering | |
| 5 — Billing | Stripe metered usage per query, tier limits, upgrade flow | |
| 6 — Polish | Langfuse tracing wired into the agent loop, README with eval numbers + demo GIF, deploy (Fly.io/Render) | |

## Explicit non-goals (for now)

- Support for non-Postgres warehouses (Snowflake, BigQuery, MySQL) — stretch, not MVP.
- Slack/Teams bot front-end — stretch.
- Semantic caching of repeated questions — stretch.
- Write access of any kind to a connected database — out of scope permanently; this product only ever reads.

## Architecture (target, post-Phase 4)

```
Next.js (TS) ── marketing/pricing (SSR) + app shell + chat UI (SSE)
        │
        ├── Clerk (auth, orgs)
        ├── Stripe (billing UI)
        │
FastAPI ─┬─ Agent loop (Claude, tool-use): list_tables / get_schema / run_sql
         ├─ (Schema RAG / pgvector — deferred; measured as unnecessary at 220 tables,
         │   see TECH_STACK.md "Why Schema RAG was deferred")
         ├─ SQL sandbox: read-only role, SELECT-only, EXPLAIN guard, timeout, row cap
         ├─ Usage metering → Stripe usage records
         └─ Eval harness (`make eval`, 50-question NL→SQL benchmark)
                │
        Postgres (app data) + Langfuse (agent tracing, Docker)
        Target DB (per-tenant, demo: synthetic SaaS-metrics dataset)
```
