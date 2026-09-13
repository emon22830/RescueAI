"""Environment configuration. Everything the app needs comes from backend/.env."""

from pydantic_settings import BaseSettings, SettingsConfigDict


class ConfigurationError(RuntimeError):
    """A required environment variable is missing. Surfaced to the client as 503."""


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # Database
    supabase_url: str = ""
    supabase_service_key: str = ""

    # LLM
    anthropic_api_key: str = ""
    llm_model: str = "claude-opus-5"

    # Integrations (filled in as each one is implemented)
    slack_bot_token: str = ""
    linear_api_key: str = ""
    github_token: str = ""
    github_repo: str = ""
    google_client_id: str = ""
    google_client_secret: str = ""
    google_refresh_token: str = ""

    cors_origins: str = "http://localhost:5173"

    def require(self, *names: str) -> None:
        """Fail with one clear message naming every variable that is missing."""
        missing = [name.upper() for name in names if not getattr(self, name)]
        if missing:
            raise ConfigurationError(
                f"Missing environment variable(s): {', '.join(missing)}. "
                "Copy backend/.env.example to backend/.env and fill them in."
            )


settings = Settings()
