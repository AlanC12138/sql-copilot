"""Conversation history replay: ordering, capping, and tenant scoping.

History is what makes follow-up questions ("and how about enterprise?") work, and
it is read back into the prompt — so a scoping mistake here would leak one org's
questions into another org's context.
"""
import uuid

from app.routers.chat import HISTORY_MAX_MESSAGES, _load_history


def test_returns_turns_oldest_first(make_org, add_turn):
    org_id = make_org()
    conv = add_turn(org_id, "first question", "first answer")
    add_turn(org_id, "second question", "second answer", conv_id=conv)

    history = _load_history(org_id, str(conv))

    assert [m["role"] for m in history] == ["user", "assistant", "user", "assistant"]
    assert [m["content"] for m in history] == [
        "first question", "first answer", "second question", "second answer",
    ]


def test_question_precedes_its_answer_despite_identical_timestamps(make_org, add_turn_answer_first):
    # Both rows of a turn are written in one transaction, so created_at ties and
    # row order is undefined. This fixture inserts the answer first, so ordering by
    # created_at alone returns them backwards — only the role tiebreaker recovers
    # the real sequence. A prompt replayed answer-first is incoherent.
    org_id = make_org()
    conv = add_turn_answer_first(org_id, "q", "a")

    history = _load_history(org_id, str(conv))

    assert [m["role"] for m in history] == ["user", "assistant"]
    assert [m["content"] for m in history] == ["q", "a"]


def test_does_not_return_another_orgs_conversation(make_org, add_turn):
    owner = make_org()
    intruder = make_org()
    conv = add_turn(owner, "confidential question", "confidential answer")

    # Same conversation id, wrong org — must come back empty, not leak.
    assert _load_history(intruder, str(conv)) == []
    assert _load_history(owner, str(conv)) != []


def test_capped_to_most_recent_messages(make_org, add_turn):
    org_id = make_org()
    conv = add_turn(org_id, "q0", "a0")
    for i in range(1, HISTORY_MAX_MESSAGES):  # 2 messages per turn, so this overflows
        add_turn(org_id, f"q{i}", f"a{i}", conv_id=conv)

    history = _load_history(org_id, str(conv))

    assert len(history) == HISTORY_MAX_MESSAGES
    # Keeps the tail, so the newest turn survives and the oldest is dropped.
    assert history[-1]["content"] == f"a{HISTORY_MAX_MESSAGES - 1}"
    assert all(m["content"] != "q0" for m in history)


def test_empty_when_no_conversation_requested(make_org):
    assert _load_history(make_org(), None) == []


def test_empty_for_unparseable_conversation_id(make_org):
    # Comes straight off a query string, so a malformed value must not 500.
    assert _load_history(make_org(), "not-a-uuid") == []


def test_empty_for_unknown_conversation(make_org):
    assert _load_history(make_org(), str(uuid.uuid4())) == []


def test_empty_without_an_org(app_engine):
    # Demo/unauthenticated path: nothing is persisted, so nothing to replay.
    assert _load_history(None, str(uuid.uuid4())) == []
