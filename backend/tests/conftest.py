import uuid

import pytest
from sqlalchemy import create_engine, text

from app.config import settings
from app.db.app_engine import get_app_engine
from app.models.tables import conversations, messages, metadata, organizations


@pytest.fixture(scope="session")
def app_engine():
    """A dedicated test database, or a skip if Postgres isn't running.

    Some behaviour here (tenant scoping, the monthly usage window) is only
    meaningfully testable against real Postgres — `date_trunc` and transaction-time
    `now()` have no faithful SQLite equivalent — so these tests need a real server
    and skip cleanly when `docker compose up app_db` hasn't been run.

    Two deliberate choices:

    - A *separate* `..._test` database, so a test run can never disturb the dev
      database's orgs and conversations.
    - `drop_all` before `create_all`. `create_all` alone no-ops on existing
      tables, so a long-lived test database would silently keep an old schema
      after a model change and pass tests that production would fail.
    """
    base_url, db_name = settings.app_database_url.rsplit("/", 1)
    test_db = f"{db_name}_test"

    # CREATE DATABASE can't run inside a transaction.
    admin = create_engine(f"{base_url}/postgres", isolation_level="AUTOCOMMIT")
    try:
        with admin.connect() as conn:
            exists = conn.execute(
                text("SELECT 1 FROM pg_database WHERE datname = :n"), {"n": test_db}
            ).first()
            if not exists:
                conn.execute(text(f'CREATE DATABASE "{test_db}"'))
    except Exception as exc:  # pragma: no cover - environment dependent
        pytest.skip(f"app database unavailable ({type(exc).__name__}) — run `make start`")
    finally:
        admin.dispose()

    # Point the app's own engine at the test database and rebuild it. Code under
    # test (e.g. _load_history, _over_global_budget) calls get_app_engine()
    # internally rather than taking an engine, so handing the fixture a separate
    # engine would leave the tests and the code reading different databases.
    # get_app_engine is lru_cached and resolves settings at call time, so
    # clearing the cache redirects every caller, including modules that imported
    # the function directly.
    settings.app_database_url = f"{base_url}/{test_db}"
    get_app_engine.cache_clear()
    engine = get_app_engine()

    metadata.drop_all(engine)
    metadata.create_all(engine)
    yield engine
    get_app_engine.cache_clear()


@pytest.fixture
def make_org(app_engine):
    """Create throwaway orgs, cleaned up afterwards (cascades to their conversations)."""
    created: list[uuid.UUID] = []

    def _make(tier: str = "free") -> uuid.UUID:
        org_id = uuid.uuid4()
        with app_engine.begin() as conn:
            conn.execute(organizations.insert().values(
                id=org_id,
                clerk_org_id=f"test_org_{org_id}",
                name="test org",
                tier=tier,
            ))
        created.append(org_id)
        return org_id

    yield _make

    with app_engine.begin() as conn:
        for org_id in created:
            conn.execute(organizations.delete().where(organizations.c.id == org_id))


@pytest.fixture
def add_turn(app_engine):
    """Persist one question/answer pair the way the chat router does.

    Both rows go in a single transaction on purpose: Postgres `now()` is the
    transaction timestamp, so they land with identical created_at values. That is
    exactly the case history ordering has to survive.
    """
    def _add(org_id: uuid.UUID, question: str, answer: str, conv_id: uuid.UUID | None = None) -> uuid.UUID:
        with app_engine.begin() as conn:
            if conv_id is None:
                conv_id = uuid.uuid4()
                conn.execute(conversations.insert().values(
                    id=conv_id, org_id=org_id, clerk_user_id="user_test",
                ))
            conn.execute(messages.insert().values(
                id=uuid.uuid4(), conversation_id=conv_id, role="user", content=question,
            ))
            conn.execute(messages.insert().values(
                id=uuid.uuid4(), conversation_id=conv_id, role="assistant", content=answer,
            ))
        return conv_id

    return _add


@pytest.fixture
def add_turn_answer_first(app_engine):
    """Same as add_turn, but writes the answer row before the question row.

    Physical insert order is the only thing distinguishing the two rows once their
    created_at values tie, so writing them backwards is what actually exercises the
    ordering tiebreaker rather than relying on Postgres happening to return rows in
    insert order.
    """
    def _add(org_id: uuid.UUID, question: str, answer: str) -> uuid.UUID:
        conv_id = uuid.uuid4()
        with app_engine.begin() as conn:
            conn.execute(conversations.insert().values(
                id=conv_id, org_id=org_id, clerk_user_id="user_test",
            ))
            conn.execute(messages.insert().values(
                id=uuid.uuid4(), conversation_id=conv_id, role="assistant", content=answer,
            ))
            conn.execute(messages.insert().values(
                id=uuid.uuid4(), conversation_id=conv_id, role="user", content=question,
            ))
        return conv_id

    return _add
