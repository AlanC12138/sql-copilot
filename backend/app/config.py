from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

    anthropic_api_key: str = ""
    claude_model: str = "claude-sonnet-4-6"

    demo_database_url: str = "postgresql+psycopg2://copilot_readonly:copilot_readonly@localhost:5432/sql_copilot_demo"
    demo_database_admin_url: str = "postgresql+psycopg2://postgres:postgres@localhost:5432/sql_copilot_demo"

    sandbox_max_rows: int = 1000
    sandbox_statement_timeout_ms: int = 5000
    sandbox_max_plan_cost: float = 100_000.0

    agent_max_turns: int = 8


settings = Settings()
