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

    free_tier_monthly_query_limit: int = 20
    free_tier_max_rows: int = 1000
    free_tier_statement_timeout_ms: int = 5000
    pro_tier_max_rows: int = 5000
    pro_tier_statement_timeout_ms: int = 15000


settings = Settings()
