"""Executes LLM-generated SQL safely.

Defense in depth, in order:
1. Structural validation (single statement, SELECT or SELECT-with-CTE only).
2. A full-text keyword blocklist — Postgres allows data-modifying statements inside a
   WITH clause (`WITH x AS (DELETE FROM t RETURNING *) SELECT * FROM x`), so checking
   only the first token would let a write smuggle in through a CTE body.
3. An EXPLAIN cost guard and a statement timeout, to bound expensive read queries.
4. The database connection itself uses a role granted SELECT only — the real backstop
   if a validation gap ever lets something through.

None of this can fully "parameterize" the query, because the whole statement is the
dynamic part by design. The safety model is structural validation + a read-only
privilege boundary, not query parameterization.
"""
import re
from dataclasses import dataclass
from typing import Any

import sqlparse
from sqlalchemy.engine import Engine

FORBIDDEN_KEYWORDS = (
    "INSERT", "UPDATE", "DELETE", "DROP", "ALTER", "TRUNCATE", "CREATE",
    "GRANT", "REVOKE", "MERGE", "CALL", "EXECUTE", "COPY", "VACUUM", "REINDEX",
)


class SandboxError(Exception):
    """Raised when a query is rejected before or during execution."""


@dataclass
class QueryResult:
    columns: list[str]
    rows: list[list[Any]]
    row_count: int
    truncated: bool


def validate_select_only(sql: str) -> None:
    statements = [s for s in sqlparse.parse(sql) if s.token_first(skip_cm=True) is not None]
    if len(statements) != 1:
        raise SandboxError("Only a single SQL statement is allowed.")

    first_token = statements[0].token_first(skip_cm=True)
    keyword = (first_token.value or "").upper()
    if keyword not in ("SELECT", "WITH"):
        raise SandboxError("Only SELECT statements (optionally with a leading CTE) are allowed.")

    upper_sql = sql.upper()
    for forbidden in FORBIDDEN_KEYWORDS:
        if re.search(rf"\b{forbidden}\b", upper_sql):
            raise SandboxError(f"Statement contains a forbidden keyword: {forbidden}")


def check_plan_cost(conn, sql: str, max_cost: float) -> None:
    plan = conn.exec_driver_sql(f"EXPLAIN (FORMAT JSON) {sql}").scalar()
    total_cost = plan[0]["Plan"]["Total Cost"]
    if total_cost > max_cost:
        raise SandboxError(
            f"Estimated query cost ({total_cost:.0f}) exceeds the sandbox limit ({max_cost:.0f})."
        )


def run_query(engine: Engine, sql: str, max_rows: int, timeout_ms: int, max_cost: float) -> QueryResult:
    validate_select_only(sql)

    with engine.connect() as conn:
        conn.exec_driver_sql(f"SET statement_timeout = {int(timeout_ms)}")
        check_plan_cost(conn, sql, max_cost)

        result = conn.exec_driver_sql(sql)
        columns = list(result.keys())
        # Fetch one extra row to detect truncation. Rewriting arbitrary SQL to inject a
        # LIMIT is unreliable (aggregates, UNIONs, existing LIMIT/OFFSET) — capping the
        # client-side fetch is simpler and combines with the cost guard/timeout above.
        fetched = result.fetchmany(max_rows + 1)
        truncated = len(fetched) > max_rows
        rows = [list(row) for row in fetched[:max_rows]]

    return QueryResult(columns=columns, rows=rows, row_count=len(rows), truncated=truncated)
