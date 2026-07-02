"""Tool schemas (Anthropic tool-use format) and their Python implementations."""
from sqlalchemy import Engine, inspect

from app.agent.sandbox import SandboxError, run_query
from app.config import settings

TOOL_SCHEMAS = [
    {
        "name": "list_tables",
        "description": "List all tables available in the connected database.",
        "input_schema": {"type": "object", "properties": {}},
    },
    {
        "name": "get_schema",
        "description": "Get column names, types, primary key, and foreign keys for a specific table.",
        "input_schema": {
            "type": "object",
            "properties": {"table_name": {"type": "string"}},
            "required": ["table_name"],
        },
    },
    {
        "name": "run_sql",
        "description": (
            "Execute a single read-only SELECT statement (CTEs allowed) against the "
            "connected database and return the result rows."
        ),
        "input_schema": {
            "type": "object",
            "properties": {"query": {"type": "string"}},
            "required": ["query"],
        },
    },
]


def list_tables(engine: Engine) -> dict:
    return {"tables": inspect(engine).get_table_names(schema="public")}


def get_schema(engine: Engine, table_name: str) -> dict:
    inspector = inspect(engine)
    available = inspector.get_table_names(schema="public")
    if table_name not in available:
        return {"error": f"Unknown table '{table_name}'. Available tables: {available}"}

    columns = inspector.get_columns(table_name, schema="public")
    pk = inspector.get_pk_constraint(table_name, schema="public")
    fks = inspector.get_foreign_keys(table_name, schema="public")
    return {
        "table": table_name,
        "columns": [
            {"name": c["name"], "type": str(c["type"]), "nullable": c["nullable"]} for c in columns
        ],
        "primary_key": pk.get("constrained_columns", []),
        "foreign_keys": [
            {
                "columns": fk["constrained_columns"],
                "references": f"{fk['referred_table']}({', '.join(fk['referred_columns'])})",
            }
            for fk in fks
        ],
    }


def run_sql(engine: Engine, query: str) -> dict:
    try:
        result = run_query(
            engine,
            query,
            max_rows=settings.sandbox_max_rows,
            timeout_ms=settings.sandbox_statement_timeout_ms,
            max_cost=settings.sandbox_max_plan_cost,
        )
    except SandboxError as exc:
        return {"error": str(exc)}
    except Exception as exc:
        # A structurally valid SELECT can still fail at the DB level (unknown column,
        # type mismatch, etc). Surface it as a tool error so the agent can retry once.
        return {"error": f"Query failed: {exc}"}

    return {
        "columns": result.columns,
        "rows": result.rows,
        "row_count": result.row_count,
        "truncated": result.truncated,
    }


def call_tool(name: str, tool_input: dict, engine: Engine) -> dict:
    if name == "list_tables":
        return list_tables(engine)
    if name == "get_schema":
        return get_schema(engine, **tool_input)
    if name == "run_sql":
        return run_sql(engine, **tool_input)
    return {"error": f"Unknown tool: {name}"}
