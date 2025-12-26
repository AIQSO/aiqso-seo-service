from functools import lru_cache
from typing import Literal

from pydantic import field_validator
from pydantic_settings import BaseSettings


class SettingsValidationError(ValueError):
    """Raised when required runtime settings are missing or unsafe."""


class Settings(BaseSettings):
    """Application settings."""

    # App
    app_name: str = "AIQSO SEO Service"
    app_version: str = "1.0.0"
    debug: bool = False
    api_prefix: str = "/api/v1"
    environment: Literal["development", "staging", "production", "test"] = "development"

    # Logging
    log_level: str = "INFO"
    log_json: bool = False

    # Database
    database_url: str = "postgresql://seo_user:seo_pass@localhost:5432/aiqso_seo"
    db_auto_create: bool = True  # Create tables on startup (dev-friendly; prefer migrations in production)

    # Redis (for Celery)
    redis_url: str = "redis://localhost:6379/0"

    # SerpBear integration
    serpbear_url: str = "http://localhost:3000"
    serpbear_api_key: str = ""
    serpbear_user: str = "admin"
    serpbear_password: str = ""
    serpbear_secret: str = ""
    serpbear_public_url: str = ""

    # Database password (for docker-compose)
    db_password: str = ""

    # Scraping API (for SERP data)
    scraping_api_key: str = ""
    scraping_api_provider: str = "scrapingant"  # scrapingant, serper, etc.

    # Anthropic (for AI insights)
    anthropic_api_key: str = ""

    # AIQSO AI Server
    ai_server_url: str = "https://ai-api.aiqso.io"

    # Stripe (for billing)
    stripe_secret_key: str = ""
    stripe_publishable_key: str = ""
    stripe_webhook_secret: str = ""

    # Odoo ERP (for client management)
    odoo_url: str = ""  # e.g., https://your-odoo.odoo.com
    odoo_database: str = ""
    odoo_username: str = ""
    odoo_api_key: str = ""

    # App URL (for callbacks)
    app_url: str = "https://seo.aiqso.io"

    # Security
    secret_key: str = "change-this-in-production"
    access_token_expire_minutes: int = 60 * 24 * 7  # 7 days
    require_api_key: bool = False  # When true, require X-API-Key or Authorization: Bearer for most API routes

    # CORS - accepts comma-separated string or list
    cors_origins: str | list[str] = "http://localhost:3000,https://aiqso.io"

    @field_validator("cors_origins", mode="before")
    @classmethod
    def parse_cors_origins(cls, v):
        if isinstance(v, str):
            return [origin.strip() for origin in v.split(",") if origin.strip()]
        return v

    # Lighthouse
    lighthouse_enabled: bool = True
    chrome_path: str = "/usr/bin/google-chrome"

    # Limits
    max_pages_per_audit: int = 500
    max_concurrent_audits: int = 5
    audit_timeout_seconds: int = 300

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        extra = "ignore"  # Allow extra env vars not defined in Settings

    def validate_runtime(self) -> None:
        """
        Validate settings for runtime safety.

        Keep this intentionally conservative: validate obvious misconfigurations that would
        cause insecure production deployments or hard-to-debug runtime failures.
        """
        errors: list[str] = []

        if self.environment == "production" and self.debug:
            errors.append("DEBUG must be false in production.")

        if self.environment in {"staging", "production"}:
            if self.secret_key == "change-this-in-production" or len(self.secret_key) < 32:
                errors.append("SECRET_KEY must be set to a long random value (>= 32 chars) in staging/production.")

        if (
            self.require_api_key
            and self.environment in {"staging", "production"}
            and self.secret_key == "change-this-in-production"
        ):
            errors.append("REQUIRE_API_KEY is enabled but SECRET_KEY is unsafe; set SECRET_KEY.")

        if not self.database_url:
            errors.append("DATABASE_URL must be set.")

        if errors:
            raise SettingsValidationError("Invalid configuration: " + " ".join(errors))


@lru_cache
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()
