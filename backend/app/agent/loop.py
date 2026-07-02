import json
from dataclasses import dataclass, field
from functools import lru_cache
from typing import Any, Generator

import anthropic
from sqlalchemy import Engine

from app.agent.tools import TOOL_SCHEMAS, call_tool
from app.config import settings

SYSTEM_PROMPT = """You are a data analyst assistant with read-only access to a database.

Always call `list_tables` and `get_schema` before writing SQL unless you already know \
the exact schema from earlier in this conversation. Write a single PostgreSQL SELECT \
statement (CTEs are fine) and run it with `run_sql`. If `run_sql` returns an error, \
read the error, fix the query, and try again exactly once — if it fails a second time, \
explain the problem to the user instead of guessing further.

When you have an answer, respond with a short natural-language summary followed by the \
exact SQL you ran, so the user can verify it.
"""


@dataclass
class AgentResult:
    answer: str
    sql: str | None = None
    columns: list[str] | None = None
    rows: list[list[Any]] | None = None
    truncated: bool = False
    failed: bool = False
    trace: list[dict] = field(default_factory=list)


@lru_cache
def _get_client() -> anthropic.Anthropic:
    return anthropic.Anthropic(api_key=settings.anthropic_api_key)


def _resolve_engine(engine: Engine | None) -> Engine:
    if engine is not None:
        return engine
    from app.db.demo_engine import get_demo_engine
    return get_demo_engine()


def run_agent_stream(
    question: str, engine: Engine | None = None, max_turns: int | None = None
) -> Generator[dict, None, None]:
    """Yield SSE-compatible event dicts as the agent works through the question."""
    engine = _resolve_engine(engine)
    client = _get_client()
    max_turns = max_turns or settings.agent_max_turns

    messages: list[dict] = [{"role": "user", "content": question}]
    last_sql: str | None = None
    last_result: dict | None = None
    consecutive_sql_failures = 0

    for _ in range(max_turns):
        response = client.messages.create(
            model=settings.claude_model,
            max_tokens=1024,
            system=SYSTEM_PROMPT,
            tools=TOOL_SCHEMAS,
            messages=messages,
        )
        messages.append({"role": "assistant", "content": response.content})

        if response.stop_reason != "tool_use":
            answer = "".join(block.text for block in response.content if block.type == "text")
            yield {
                "type": "answer",
                "answer": answer,
                "sql": last_sql,
                "columns": (last_result or {}).get("columns"),
                "rows": (last_result or {}).get("rows"),
                "truncated": (last_result or {}).get("truncated", False),
            }
            return

        tool_results = []
        for block in response.content:
            if block.type != "tool_use":
                continue

            yield {"type": "tool_call", "tool": block.name, "input": dict(block.input)}

            result = call_tool(block.name, block.input, engine)

            yield {"type": "tool_result", "tool": block.name, "result": result}

            if block.name == "run_sql":
                if "error" in result:
                    consecutive_sql_failures += 1
                else:
                    consecutive_sql_failures = 0
                    last_sql = block.input.get("query")
                    last_result = result

            tool_results.append({
                "type": "tool_result",
                "tool_use_id": block.id,
                "content": json.dumps(result, default=str),
                "is_error": "error" in result,
            })

        if consecutive_sql_failures >= 2:
            yield {
                "type": "answer",
                "answer": (
                    "I couldn't write a working query for that after two attempts. "
                    "Could you rephrase the question or point me at specific tables/columns?"
                ),
                "sql": None,
                "columns": None,
                "rows": None,
                "truncated": False,
                "failed": True,
            }
            return

        messages.append({"role": "user", "content": tool_results})

    yield {
        "type": "answer",
        "answer": "I wasn't able to finish answering that within the allotted reasoning steps.",
        "sql": None,
        "columns": None,
        "rows": None,
        "truncated": False,
        "failed": True,
    }


def run_agent(question: str, engine: Engine | None = None, max_turns: int | None = None) -> AgentResult:
    engine = _resolve_engine(engine)
    trace: list[dict] = []
    last_event: dict | None = None

    for event in run_agent_stream(question, engine=engine, max_turns=max_turns):
        trace.append(event)
        last_event = event

    if last_event and last_event["type"] == "answer":
        return AgentResult(
            answer=last_event["answer"],
            sql=last_event.get("sql"),
            columns=last_event.get("columns"),
            rows=last_event.get("rows"),
            truncated=last_event.get("truncated", False),
            failed=last_event.get("failed", False),
            trace=trace,
        )

    return AgentResult(
        answer="Agent finished without producing an answer.",
        failed=True,
        trace=trace,
    )
