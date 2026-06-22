import pytest

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
