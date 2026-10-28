from pydantic_settings import BaseSettings
from dotenv import load_dotenv
import os

load_dotenv()


class Settings(BaseSettings):
    DATABASE_URL: str = os.getenv("DATABASE_URL", "")
    SECRET_KEY: str = os.getenv("SECRET_KEY", "")
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 10080
    STRIPE_SECRET_KEY: str = os.getenv("STRIPE_SECRET_KEY", "")
    STRIPE_WEBHOOK_SECRET: str = os.getenv("STRIPE_WEBHOOK_SECRET", "")
    OLLAMA_HOST: str = os.getenv("OLLAMA_HOST", "http://localhost:11434")
    LLM_MODEL: str = os.getenv("LLM_MODEL", "llama3.2:3b")

    # Comma-separated list of allowed origins, e.g. "http://localhost:3000,https://myapp.com"
    CORS_ORIGINS: str = os.getenv("CORS_ORIGINS", "http://localhost:3000")

    def cors_origins_list(self) -> list[str]:
        return [origin.strip() for origin in self.CORS_ORIGINS.split(",") if origin.strip()]


settings = Settings()

# Fail fast: a missing DATABASE_URL or SECRET_KEY should never fall back
# silently to an insecure or broken default.
if not settings.DATABASE_URL:
    raise RuntimeError(
        "DATABASE_URL is not set. Define it in your .env file."
    )

if not settings.SECRET_KEY:
    raise RuntimeError(
        "SECRET_KEY is not set. Define it in your .env file "
        "(generate one with: python -c \"import secrets; print(secrets.token_urlsafe(32))\")."
    )

if len(settings.SECRET_KEY) < 32:
    raise RuntimeError(
        "SECRET_KEY is too short (must be at least 32 characters). "
        "Generate a strong one with: python -c \"import secrets; print(secrets.token_urlsafe(32))\"."
    )
