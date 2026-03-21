from __future__ import annotations

import hashlib
import hmac
import ipaddress
from urllib.parse import urlparse

from fastapi import Depends, Header, HTTPException, Request
from sqlalchemy.orm import Session

from app.config import get_settings
from app.database import get_db
from app.models.client import Client


def hash_api_key(api_key: str) -> str:
    """Hash an API key for secure storage using SHA-256."""
    return hashlib.sha256(api_key.encode()).hexdigest()


def verify_api_key(api_key: str, hashed: str) -> bool:
    """Constant-time comparison of API key against stored hash."""
    return hmac.compare_digest(hash_api_key(api_key), hashed)


def _extract_api_key(*, authorization: str | None, x_api_key: str | None) -> str | None:
    if x_api_key:
        return x_api_key.strip()
    if not authorization:
        return None
    # Accept "Bearer <key>" for compatibility with the OpenAPI description in app/main.py
    if authorization.lower().startswith("bearer "):
        return authorization.split(" ", 1)[1].strip() or None
    return None


def require_client(
    request: Request,
    authorization: str | None = Header(default=None, alias="Authorization"),
    x_api_key: str | None = Header(default=None, alias="X-API-Key"),
    db: Session = Depends(get_db),
) -> Client | None:
    """
    Optional API key auth guard.

    - When `REQUIRE_API_KEY=false` (default), this is a no-op and returns `None`.
    - When enabled, it requires either `X-API-Key` or `Authorization: Bearer ...` and
      validates it against `Client.api_key_hash`.
    """
    settings = get_settings()
    if not settings.require_api_key:
        return None

    api_key = _extract_api_key(authorization=authorization, x_api_key=x_api_key)
    if not api_key:
        raise HTTPException(status_code=401, detail="API key required")

    # Try hash-based lookup first (new format), fall back to plaintext (migration period)
    api_key_hash = hash_api_key(api_key)
    client = db.query(Client).filter(Client.api_key_hash == api_key_hash).first()

    if not client:
        # Fall back to plaintext comparison during migration period
        client = db.query(Client).filter(Client.api_key == api_key).first()
        if client:
            # Migrate: store hash and clear plaintext
            client.api_key_hash = api_key_hash
            db.commit()

    if not client:
        raise HTTPException(status_code=401, detail="Invalid API key")
    return client


# SSRF protection for audit URLs
_BLOCKED_NETWORKS = [
    ipaddress.ip_network("10.0.0.0/8"),
    ipaddress.ip_network("172.16.0.0/12"),
    ipaddress.ip_network("192.168.0.0/16"),
    ipaddress.ip_network("127.0.0.0/8"),
    ipaddress.ip_network("169.254.0.0/16"),
    ipaddress.ip_network("::1/128"),
    ipaddress.ip_network("fc00::/7"),
    ipaddress.ip_network("fe80::/10"),
]


def validate_audit_url(url: str) -> str:
    """
    Validate a URL is safe to fetch (SSRF protection).

    Raises ValueError if the URL targets internal networks or uses disallowed schemes.
    """
    parsed = urlparse(url)

    if parsed.scheme not in ("http", "https"):
        raise ValueError(f"Unsupported URL scheme: {parsed.scheme}")

    hostname = parsed.hostname
    if not hostname:
        raise ValueError("URL must have a hostname")

    # Block obvious internal hostnames
    blocked_hostnames = {"localhost", "metadata.google.internal", "169.254.169.254"}
    if hostname.lower() in blocked_hostnames:
        raise ValueError(f"Blocked hostname: {hostname}")

    # Resolve and check IP ranges
    try:
        import socket

        resolved = socket.getaddrinfo(hostname, None)
        for _, _, _, _, sockaddr in resolved:
            ip = ipaddress.ip_address(sockaddr[0])
            for network in _BLOCKED_NETWORKS:
                if ip in network:
                    raise ValueError(f"URL resolves to blocked network range: {network}")
    except socket.gaierror:
        raise ValueError(f"Cannot resolve hostname: {hostname}")

    return url
