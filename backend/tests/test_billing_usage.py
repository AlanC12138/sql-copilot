"""Monthly usage counting and free-tier gating.

This is the number the free tier is enforced on, so it has to count the right rows
for the right org — over-counting locks a paying-adjacent user out, under-counting
gives the tier away.
"""
from app.billing.usage import get_monthly_usage
from app.routers.chat import _over_free_tier_limit


def test_new_org_has_no_usage(app_engine, make_org):
    assert get_monthly_usage(app_engine, make_org()) == 0


def test_counts_one_per_question_not_per_message(app_engine, make_org, add_turn):
    # Each turn writes a user row and an assistant row; only the question is billable.
    org_id = make_org()
    conv = add_turn(org_id, "q1", "a1")
    add_turn(org_id, "q2", "a2", conv_id=conv)

    assert get_monthly_usage(app_engine, org_id) == 2


def test_counts_across_separate_conversations(app_engine, make_org, add_turn):
    org_id = make_org()
    add_turn(org_id, "q1", "a1")
    add_turn(org_id, "q2", "a2")  # new conversation

    assert get_monthly_usage(app_engine, org_id) == 2


def test_usage_is_scoped_to_the_org(app_engine, make_org, add_turn):
    # One tenant's questions must never count against another's quota.
    a, b = make_org(), make_org()
    for i in range(3):
        add_turn(a, f"q{i}", f"a{i}")

    assert get_monthly_usage(app_engine, a) == 3
    assert get_monthly_usage(app_engine, b) == 0


def test_free_tier_blocks_only_at_the_limit(make_org, add_turn, monkeypatch):
    import app.routers.chat as chat

    monkeypatch.setattr(chat.settings, "free_tier_monthly_query_limit", 2)
    org_id = make_org(tier="free")

    add_turn(org_id, "q1", "a1")
    assert _over_free_tier_limit(org_id, "free") is False, "under the cap should pass"

    add_turn(org_id, "q2", "a2")
    assert _over_free_tier_limit(org_id, "free") is True, "at the cap should block"


def test_pro_tier_is_never_blocked(make_org, add_turn, monkeypatch):
    import app.routers.chat as chat

    monkeypatch.setattr(chat.settings, "free_tier_monthly_query_limit", 1)
    org_id = make_org(tier="pro")
    for i in range(5):
        add_turn(org_id, f"q{i}", f"a{i}")

    assert _over_free_tier_limit(org_id, "pro") is False


def test_demo_path_without_an_org_is_never_blocked():
    # No org means nothing is persisted, so there's no usage to meter.
    assert _over_free_tier_limit(None, "free") is False
