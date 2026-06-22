# SQL Copilot — Tech Stack

> Each choice includes why it fits *this* project specifically — not copied from other repos in this workspace.

---

## Backend

| Concern | Choice | Notes |
|---|---|---|
| Language | Python 3.13+ | Strongest SDK support for Anthropic/OpenAI, native tooling for schema reflection and eval scoring |
| Web framework | FastAPI | Async-native — needed for streaming agent reasoning steps over SSE in Phase 4 |
| Dependency management | Poetry | Lock file, clean packaging |
| ORM / DB toolkit | SQLAlchemy 2.0 (Core, not ORM, for the *target* DB) | `inspect()` reflection is exactly what `get_schema` needs against an arbitrary, unknown schema. ORM models only apply to the *app* DB (orgs/users/connections), introduced in Phase 3 |
| Migrations | Alembic | App DB schema versioning, from Phase 3 onward |
| SQL parsing/validation | `sqlparse` | Used by the sandbox to reject multi-statement input and non-SELECT statements before execution |

## AI / Agent

| Concern | Choice | Notes |
|---|---|---|
| LLM | Claude (Anthropic SDK), provider abstracted behind an interface | Strong at multi-step tool-use loops, which is the core mechanic here. Swappable — the Phase 2 eval harness can benchmark alternatives empirically instead of by assertion |
| Agent orchestration | Hand-rolled tool-use loop (no LangGraph) | The safety sandbox needs tight coupling to the tool-execution step (intercept SQL before running it); a thin custom loop gives more control than a framework would for a 3-tool, bounded-turn loop |
| Schema RAG | pgvector | Schema metadata is small (tens–hundreds of vectors per tenant) — co-locating with relational tenant data in Postgres avoids running a second vector service for a workload this size |

## Data Storage

| Concern | Choice | Notes |
|---|---|---|
| App database | PostgreSQL | Introduced in Phase 3 (orgs, users, connections, conversations, usage events) |
| Target/demo database | PostgreSQL | Best SQLAlchemy reflection support; most common OLTP demo target |
| SQL execution role | Dedicated read-only Postgres role, `SELECT`-only grants | Primary defense against destructive/runaway queries is the database privilege boundary itself — the application-level `sqlparse` check is a second layer, not the only one |

## Auth & Billing (Phase 3 / 5)

| Concern | Choice | Notes |
|---|---|---|
| Auth | Clerk | Multi-tenant orgs are core to the product, not incidental — buying this beats re-implementing what every real SaaS already has |
| Billing | Stripe, metered usage + tiered subscriptions | Free tier capped by query count, Pro tier unlimited with higher sandbox limits |

## Frontend (Phase 4)

| Concern | Choice | Notes |
|---|---|---|
| Framework | Next.js (App Router) + TypeScript + Tailwind | Needs SSR'd public marketing/pricing pages *and* an authenticated app shell in one framework; Clerk and Stripe both have their most polished integration paths for Next.js |
| Charting | Recharts | Auto-picks chart type from result shape |

## Observability & Eval (Phase 2 / 6)

| Concern | Choice | Notes |
|---|---|---|
| LLM/agent tracing | Langfuse (self-hosted, Docker) | Purpose-built for tool-call traces, token cost, latency, per-conversation replay — a generic log table doesn't capture this for an agent |
| Eval harness | Custom Python script, fixed 50 NL→SQL pairs, exact-match + execution-match scoring | Run via `make eval`; the quantifiable artifact and the regression guard for prompt iteration |

## Infra

| Concern | Choice | Notes |
|---|---|---|
| Local dev | Docker Compose | Postgres (+ Langfuse from Phase 6) |
| Deploy | Fly.io or Render | Cloud SaaS target, not desktop packaging |
