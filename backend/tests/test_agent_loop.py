"""Agent loop control flow, with the model and tools stubbed out.

These stay pure unit tests — no network, no database — so the loop's guardrails
(history replay, tier limits, giving up) are covered without spending API credit.
"""
from contextlib import contextmanager

import pytest

import app.agent.loop as loop


class FakeBlock:
    """Stands in for an Anthropic content block (text or tool_use)."""

    def __init__(self, type, text=None, name=None, input=None, id="tu_1"):
        self.type = type
        self.text = text
        self.name = name
        self.input = input or {}
        self.id = id

    def model_dump(self):  # the loop serialises blocks for the Langfuse generation
        return {"type": self.type, "text": self.text, "name": self.name}


class FakeUsage:
    input_tokens = 10
    output_tokens = 5


class FakeResponse:
    def __init__(self, content, stop_reason):
        self.content = content
        self.stop_reason = stop_reason
        self.usage = FakeUsage()


class FakeMessages:
    def __init__(self, responses):
        self._responses = list(responses)
        self.calls = []

    def create(self, **kwargs):
        # Snapshot `messages`: the loop appends to that same list as it goes, so
        # holding the reference would show later turns' state, not this call's.
        self.calls.append({**kwargs, "messages": list(kwargs["messages"])})
        # Repeat the last scripted response once the script runs out.
        return self._responses.pop(0) if len(self._responses) > 1 else self._responses[0]


class FakeClient:
    def __init__(self, responses):
        self.messages = FakeMessages(responses)


class _Obs:
    def update(self, **kwargs):
        pass


class FakeLangfuse:
    @contextmanager
    def start_as_current_observation(self, **kwargs):
        yield _Obs()

    def flush(self):
        pass


def answer_response(text="done"):
    return FakeResponse([FakeBlock("text", text=text)], stop_reason="end_turn")


def tool_response(name="run_sql", tool_input=None):
    return FakeResponse(
        [FakeBlock("tool_use", name=name, input=tool_input or {"query": "SELECT 1"})],
        stop_reason="tool_use",
    )


@pytest.fixture
def patched(monkeypatch):
    """Install fake model/tracing and a spy on tool execution."""
    monkeypatch.setattr(loop, "_get_langfuse", lambda: FakeLangfuse())
    calls = {"tool": []}

    def install(responses, tool_result=None):
        client = FakeClient(responses)
        monkeypatch.setattr(loop, "_get_client", lambda: client)

        def fake_call_tool(name, tool_input, engine, max_rows, timeout_ms):
            calls["tool"].append(
                {"name": name, "input": tool_input, "max_rows": max_rows, "timeout_ms": timeout_ms}
            )
            return tool_result if tool_result is not None else {"columns": ["x"], "rows": [[1]]}

        monkeypatch.setattr(loop, "call_tool", fake_call_tool)
        return client, calls

    return install


def drain(**kwargs):
    return list(loop.run_agent_stream("current question", engine=object(), **kwargs))


def test_history_is_replayed_before_the_new_question(patched):
    client, _ = patched([answer_response()])
    history = [
        {"role": "user", "content": "earlier question"},
        {"role": "assistant", "content": "earlier answer"},
    ]

    drain(history=history)

    sent = client.messages.calls[0]["messages"]
    assert sent == history + [{"role": "user", "content": "current question"}]


def test_without_history_only_the_question_is_sent(patched):
    client, _ = patched([answer_response()])

    drain()

    assert client.messages.calls[0]["messages"] == [
        {"role": "user", "content": "current question"}
    ]


def test_tier_limits_are_passed_through_to_the_sandbox(patched):
    # Pro-tier callers must actually get the wider row cap and timeout, not defaults.
    _, calls = patched([tool_response(), answer_response()])

    drain(max_rows=5000, timeout_ms=15000)

    assert calls["tool"][0]["max_rows"] == 5000
    assert calls["tool"][0]["timeout_ms"] == 15000


def test_defaults_to_free_tier_limits(patched):
    _, calls = patched([tool_response(), answer_response()])

    drain()

    assert calls["tool"][0]["max_rows"] == loop.settings.free_tier_max_rows
    assert calls["tool"][0]["timeout_ms"] == loop.settings.free_tier_statement_timeout_ms


def test_gives_up_after_two_consecutive_sql_failures(patched):
    # Guards the "self-correct once, then stop" rule — without it a broken query
    # burns the whole turn budget retrying.
    _, calls = patched([tool_response()], tool_result={"error": "boom"})

    events = drain()

    final = events[-1]
    assert final["type"] == "answer"
    assert final["failed"] is True
    assert "two attempts" in final["answer"]
    assert len(calls["tool"]) == 2, "should stop after the second failure, not keep retrying"


def test_stops_at_max_turns_when_the_model_never_finishes(patched):
    _, _ = patched([tool_response(name="list_tables", tool_input={})])

    events = drain(max_turns=3)

    final = events[-1]
    assert final["type"] == "answer"
    assert final["failed"] is True
    assert "allotted reasoning steps" in final["answer"]


def test_successful_run_reports_sql_and_rows(patched):
    _, _ = patched([tool_response(tool_input={"query": "SELECT 1"}), answer_response("all good")])

    events = drain()

    final = events[-1]
    assert final["type"] == "answer"
    assert final["answer"] == "all good"
    assert final["sql"] == "SELECT 1"
    assert final["rows"] == [[1]]
    assert final.get("failed", False) is False


def test_stream_emits_tool_call_and_result_events(patched):
    _, _ = patched([tool_response(), answer_response()])

    kinds = [e["type"] for e in drain()]

    assert kinds == ["tool_call", "tool_result", "answer"]


def test_run_agent_returns_structured_result(patched):
    _, _ = patched([tool_response(), answer_response("summary")])

    result = loop.run_agent("q", engine=object())

    assert result.answer == "summary"
    assert result.sql == "SELECT 1"
    assert result.failed is False
