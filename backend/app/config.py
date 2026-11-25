from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

    anthropic_api_key: str = ""
    claude_model: str = "claude-sonnet-4-6"

    demo_database_url: str = "postgresql+psycopg2://copilot_readonly:copilot_readonly@localhost:5432/sql_copilot_demo"
    demo_database_admin_url: str = "postgresql+psycopg2://postgres:postgres@localhost:5432/sql_copilot_demo"
    app_database_url: str = "postgresql+psycopg2://postgres:postgres@localhost:5433/sql_copilot_app"

    sandbox_max_plan_cost: float = 100_000.0

    agent_max_turns: int = 8

    clerk_secret_key: str = ""
    disable_auth: bool = False

    encryption_key: str = ""

    stripe_secret_key: str = ""
    stripe_webhook_secret: str = ""
    stripe_price_id_pro: str = ""
    frontend_url: str = "http://localhost:3000"
    # Comma-separated browser origins allowed to call this API. Must include the
    # deployed frontend's origin or every request from it fails CORS.
    cors_origins: str = "http://localhost:3000"

    free_tier_monthly_query_limit: int = 20
    # Hard ceiling across ALL orgs, as a spend backstop for a public demo: the
    # per-org free limit caps one tenant, but anyone can sign up again, so it is
    # not a budget. 0 disables the ceiling (the default, for local use).
    global_monthly_query_limit: int = 0
    free_tier_max_rows: int = 1000
    free_tier_statement_timeout_ms: int = 5000
    pro_tier_max_rows: int = 5000
    pro_tier_statement_timeout_ms: int = 15000

    langfuse_public_key: str = ""
    langfuse_secret_key: str = ""
    langfuse_host: str = "https://cloud.langfuse.com"


settings = Settings()
