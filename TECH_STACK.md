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
| Schema RAG | ~~pgvector~~ — **deferred, not built** | Originally planned (rationale: schema metadata is small, so co-locating vectors with relational tenant data in Postgres beats running a second vector service). Deferred after measuring whether it was needed — see below. The agent instead discovers schema by brute force, calling `list_tables` / `get_schema` per question. |

### Why Schema RAG was deferred

The plan assumed brute-force schema discovery would break on a realistic database. That was tested rather than assumed: `scripts/seed_bench_db.py` builds a 220-table warehouse-shaped schema (the 4 real tables plus 16 near-miss decoys and 200 noise tables), holding the data and the 50 gold queries constant so schema noise is the only variable.

| | Clean (4 tables) | Noisy (220 tables) |
|---|---|---|
| Execution-match | 43/50 (86%) | 45/50 (90%) |
| Cost per question | $0.0176 | $0.0317 |

Accuracy held — the two runs are statistically indistinguishable (failure sets barely overlap, so run-to-run variance dominates). The real costs of brute-force discovery are (a) ~80% more spend per question, since the 220-name table list rides along in every turn's context, and (b) two new failure modes: one question exhausted the turn budget during discovery, and one found empty noise tables named `support_logs` / `int_support_logs` and confidently answered "no support tickets have been raised" while the real data sat in `events`.

Those are real, but they're plausibly prompt/`agent_max_turns` problems rather than retrieval problems, and adding RAG would mean a second AI vendor (Anthropic ships no embeddings model — the docs point to Voyage AI), a pgvector index, and a schema-invalidation pipeline. Not worth that until there's a tenant whose schema actually defeats the current approach. Re-run `make eval-bench` to re-test the assumption.

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
| LLM/agent tracing | Langfuse (Cloud, free tier) | Purpose-built for tool-call traces, token cost, latency, per-conversation replay — a generic log table doesn't capture this for an agent. Originally planned as self-hosted, but Langfuse's self-host stack grew to 6 containers (Postgres, ClickHouse, Redis, MinIO, web, worker) by the time Phase 6 started — not worth the footprint for a single-dev portfolio project, so Cloud's free tier is used instead. Still swappable to self-hosted later since the SDK talks to any Langfuse-compatible host. |
| Eval harness | Custom Python script, fixed 50 NL→SQL pairs, exact-match + execution-match scoring | Run via `make eval`; the quantifiable artifact and the regression guard for prompt iteration |

## Infra

| Concern | Choice | Notes |
|---|---|---|
| Local dev | Docker Compose | Postgres (demo + app DB); Langfuse tracing points at Cloud, no local container |
| Deploy | Undecided, deferred | Fly.io was the original pick, but it dropped its free tier by the time Phase 6 started (card required, ~$4-15/mo). Render's free tier is card-free but the Postgres expires after 30 days. Not worth committing to either until this needs a real public URL. |
