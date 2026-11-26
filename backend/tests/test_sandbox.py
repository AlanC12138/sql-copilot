import json
from decimal import Decimal

import pytest

from app.agent import sandbox
from app.agent.sandbox import SandboxError, validate_select_only


def test_plain_select_passes():
    validate_select_only("SELECT * FROM customers")


def test_cte_select_passes():
    validate_select_only(
        "WITH recent AS (SELECT * FROM customers WHERE signup_date > '2025-01-01') "
        "SELECT * FROM recent"
    )


def test_multiple_statements_rejected():
    with pytest.raises(SandboxError):
        validate_select_only("SELECT * FROM customers; SELECT * FROM events")


def test_insert_rejected():
    with pytest.raises(SandboxError):
        validate_select_only("INSERT INTO customers (name) VALUES ('x')")


def test_drop_table_rejected():
    with pytest.raises(SandboxError):
        validate_select_only("DROP TABLE customers")


def test_write_smuggled_in_cte_rejected():
    with pytest.raises(SandboxError):
        validate_select_only(
            "WITH deleted AS (DELETE FROM customers RETURNING *) SELECT * FROM deleted"
        )


def test_update_smuggled_in_subquery_rejected():
    with pytest.raises(SandboxError):
        validate_select_only(
            "SELECT * FROM (UPDATE customers SET plan = 'free' RETURNING *) AS x"
        )


# --- NUMERIC serialization -------------------------------------------------
#
# Postgres returns NUMERIC as Decimal, and the agent loop and SSE stream both
# serialize with `json.dumps(..., default=str)`. Without coercion the fallback
# stringifies it at the scale the server sent, so a zero group from
# `SUM(mrr_cents) / 100.0` reached the UI and the model as `"0E-20"`.
#
# These assert the JSON round-trip rather than just the return value, because
# that is where it actually went wrong.

def test_zero_numeric_serializes_as_a_number_not_scientific_notation():
    assert json.dumps(sandbox._jsonable(Decimal("0E-20"))) == "0"


def test_whole_numeric_loses_its_trailing_scale():
    assert json.dumps(sandbox._jsonable(Decimal("10978.000000000000"))) == "10978"


def test_fractional_numeric_keeps_its_value():
    assert sandbox._jsonable(Decimal("29.99")) == pytest.approx(29.99)
    assert json.dumps(sandbox._jsonable(Decimal("29.99"))) == "29.99"


def test_non_decimal_cells_pass_through_untouched():
    for value in ("starter", 51, None, True):
        assert sandbox._jsonable(value) is value


def test_rows_are_coerced_cellwise():
    row = [["free", 24, Decimal("0E-20")], ["pro", 50, Decimal("4950.0000")]]
    coerced = [[sandbox._jsonable(c) for c in r] for r in row]
    assert json.dumps(coerced) == '[["free", 24, 0], ["pro", 50, 4950]]'
