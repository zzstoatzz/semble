from pydantic import Field, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict

DEFAULT_BASE_URL = "https://api.semble.so/xrpc"


class SembleSettings(BaseSettings):
    """client configuration from the environment and a local `.env` file.

    every field reads `SEMBLE_`-prefixed sources: `SEMBLE_API_KEY`,
    `SEMBLE_BASE_URL`, `SEMBLE_TIMEOUT`. explicit client kwargs win over
    the environment, which wins over `.env`.
    """

    model_config = SettingsConfigDict(
        env_prefix="SEMBLE_",
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    api_key: SecretStr | None = Field(
        default=None, description="API key for authentication"
    )
    base_url: str = Field(default=DEFAULT_BASE_URL, description="Base URL for the API")
    timeout: float = Field(default=30.0, description="Timeout for API requests")
