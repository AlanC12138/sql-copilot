import json
from dataclasses import dataclass, field
from functools import lru_cache
from typing import Any

import anthropic

from app.agent.tools import TOOL_SCHEMAS, call_tool
from app.config import settings

SYSTEM_PROMPT = """You are a data analyst assistant with read-only access to a SaaS \
metrics database (tables: customers, subscriptions, invoices, events).

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


def run_agent(question: str, max_turns: int | None = None) -> AgentResult:
    client = _get_client()
    max_turns = max_turns or settings.agent_max_turns

    messages: list[dict] = [{"role": "user", "content": question}]
    trace: list[dict] = []
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
            return AgentResult(
                answer=answer,
                sql=last_sql,
                columns=(last_result or {}).get("columns"),
                rows=(last_result or {}).get("rows"),
                truncated=(last_result or {}).get("truncated", False),
                trace=trace,
            )

        tool_results = []
        for block in response.content:
            if block.type != "tool_use":
                continue

            result = call_tool(block.name, block.input)
            trace.append({"tool": block.name, "input": block.input, "result": result})

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

        # First run_sql failure: feed it back below so the model gets exactly one retry.
        # Second consecutive failure: stop instead of letting the model keep guessing.
        if consecutive_sql_failures >= 2:
            return AgentResult(
                answer=(
                    "I couldn't write a working query for that after two attempts. "
                    "Could you rephrase the question or point me at specific tables/columns?"
                ),
                failed=True,
                trace=trace,
            )

        messages.append({"role": "user", "content": tool_results})

    return AgentResult(
        answer="I wasn't able to finish answering that within the allotted reasoning steps.",
        failed=True,
        trace=trace,
    )
