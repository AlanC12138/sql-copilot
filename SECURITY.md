# Security

## Scope

This is a portfolio project, not an operated service. There is no SLA and no
bug bounty. Reports are still welcome — the SQL sandbox in particular is the
part where a real finding would be interesting.

The parts worth looking at:

- **The SQL sandbox** (`backend/app/agent/sandbox.py`) — everything the model
  writes passes through it. It parses the statement, rejects anything that
  isn't a single `SELECT`/CTE, scans for forbidden keywords to catch writes
  smuggled through a CTE or subquery, runs an `EXPLAIN` cost guard, and applies
  a statement timeout and row cap. The database role it executes as is
  read-only, so the parser is defence in depth rather than the only barrier.
- **Tenant isolation** — one org must never read another's conversations or
  database connections. Scoping lives in `backend/app/routers/chat.py` and
  `connections.py`, and is covered by tests.
- **Credential handling** — tenant database URLs are encrypted at rest with
  Fernet (`backend/app/auth/crypto.py`).

## Reporting

Please open a [private security advisory](https://github.com/AlanC12138/sql-copilot/security/advisories/new)
rather than a public issue. I'll respond when I can; this is a side project, so
that may not be quickly.

## Accepted risks

These are known and deliberate for a demo of this kind — not oversights:

- **Clerk and Stripe run in development/test mode.** Keys are test keys; no real
  payment is ever processed.
- **An LLM writes the SQL.** The sandbox constrains *what* it can run, not
  whether the query is semantically the right one. The eval suite measures
  that separately, and the 220-table benchmark documents a case where the agent
  answered confidently from the wrong table — see `TECH_STACK.md`.
- **Prompt injection via database content is not mitigated.** A connected
  database whose rows contain instructions could influence the agent's replies.
  The sandbox still prevents writes, so the blast radius is wrong answers rather
  than data loss.
- **`DISABLE_AUTH=true` bypasses JWT verification entirely.** It exists for local
  development and must never be set on a deployed instance.
- **Spend.** Each question costs API credit. `GLOBAL_MONTHLY_QUERY_LIMIT` caps
  the deployment across all tenants; an Anthropic Console spend limit is the
  backstop that a bug in this code cannot bypass.

## Dependency policy

`.github/dependabot.yml` ignores semver-major bumps, so a breaking change never
arrives as an unreviewed PR. The cost is that an advisory whose fix is only in a
new major stays open until someone upgrades by hand — and because a transitive
pin can cap a direct dependency, that upgrade is sometimes not the package the
alert names. `cryptography` sat six majors behind for exactly this reason:
`clerk-backend-api` 1.x pinned it to `<44`, so clearing its advisories meant
upgrading the Clerk SDK to 7.x first.

`frontend/package.json` pins `minimatch` through `overrides`. Its advisory is a
glob-amplification denial of service reachable only from ESLint and the `shadcn`
CLI, neither of which runs in production, but the fix is a major that two
transitive parents had not yet taken. The override is verified by lint and
build, not assumed.

## Not in scope

Denial of service, rate limiting, and anything requiring an authenticated
account's own credentials to exploit.
