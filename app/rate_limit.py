"""
Rate limiting using slowapi backed by Redis.

Limits are derived from the client's tier. Unauthenticated requests
get a conservative global default.
"""

from slowapi import Limiter
from slowapi.util import get_remote_address
from starlette.requests import Request

from app.config import get_settings

settings = get_settings()

# Per-tier rate limits (requests per minute)
TIER_RATE_LIMITS = {
    "starter": "30/minute",
    "professional": "120/minute",
    "enterprise": "300/minute",
    "agency": "600/minute",
}

DEFAULT_RATE_LIMIT = "20/minute"


def _get_key(request: Request) -> str:
    """Extract rate limit key from API key header or fall back to IP."""
    api_key = request.headers.get("x-api-key") or ""
    if api_key:
        # Use a truncated hash so Redis keys aren't the full secret
        import hashlib

        return f"apikey:{hashlib.sha256(api_key.encode()).hexdigest()[:16]}"
    return get_remote_address(request)


limiter = Limiter(
    key_func=_get_key,
    storage_uri=settings.redis_url,
    default_limits=[DEFAULT_RATE_LIMIT],
    strategy="fixed-window",
)
