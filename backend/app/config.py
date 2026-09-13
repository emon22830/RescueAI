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
    gemini_api_key: str = ""
    llm_model: str = "gemini-3.8-flash"

    # Encrypts the Slack/Linear/GitHub tokens each project connects for itself, before
    # they are stored in the `integrations` table. Generate one with:
    #   python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
    credential_encryption_key: str = ""

    # Identifies this application to Google — not any one user's credential. Each
    # project grants its own access from its Connections page, and that refresh token
    # is stored encrypted per project, never here. See integrations/google_auth.py.
    google_client_id: str = ""
    google_client_secret: str = ""
    google_calendar_id: str = "primary"

    # Where Google sends the browser back after consent. Must match the authorized
    # redirect URI on the OAuth client exactly.
    backend_url: str = "http://localhost:8000"

    cors_origins: str = "http://localhost:5173"

    @property
    def app_url(self) -> str:
        """Where to send a user once an OAuth round trip is finished — the first
        allowed origin, which is the app itself."""
        return settings.cors_origins.split(",")[0].strip()

    def require(self, *names: str) -> None:
        """Fail with one clear message naming every variable that is missing."""
        missing = [name.upper() for name in names if not getattr(self, name)]
        if missing:
            raise ConfigurationError(
                f"Missing environment variable(s): {', '.join(missing)}. "
                "Copy backend/.env.example to backend/.env and fill them in."
            )


settings = Settings()
