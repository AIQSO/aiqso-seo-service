from pydantic_settings import BaseSettings
from functools import lru_cache


class Settings(BaseSettings):
    """Application settings."""

    # App
    app_name: str = "AIQSO SEO Service"
    app_version: str = "1.0.0"
    debug: bool = False
    api_prefix: str = "/api/v1"

    # Database
    database_url: str = "postgresql://seo_user:seo_pass@localhost:5432/aiqso_seo"

    # Redis (for Celery)
    redis_url: str = "redis://localhost:6379/0"

    # SerpBear integration
    serpbear_url: str = "http://localhost:3000"
    serpbear_api_key: str = ""

    # Scraping API (for SERP data)
    scraping_api_key: str = ""
    scraping_api_provider: str = "scrapingant"  # scrapingant, serper, etc.

    # Anthropic (for AI insights)
    anthropic_api_key: str = ""

    # AIQSO AI Server
    ai_server_url: str = "https://ai-api.aiqso.io"

    # Security
    secret_key: str = "change-this-in-production"
    access_token_expire_minutes: int = 60 * 24 * 7  # 7 days

    # CORS
    cors_origins: list[str] = ["http://localhost:3000", "https://aiqso.io"]

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


@lru_cache()
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()
