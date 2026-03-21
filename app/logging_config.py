import json
import logging
import sys
import uuid
from contextvars import ContextVar
from datetime import UTC, datetime
from typing import Any

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request

# Context variable for request correlation
request_id_var: ContextVar[str | None] = ContextVar("request_id", default=None)


class _JsonFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        payload: dict[str, Any] = {
            "ts": datetime.now(UTC).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }
        req_id = request_id_var.get()
        if req_id:
            payload["request_id"] = req_id
        if record.exc_info:
            payload["exc_info"] = self.formatException(record.exc_info)
        if record.stack_info:
            payload["stack_info"] = record.stack_info
        return json.dumps(payload, ensure_ascii=False)


class _TextFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        req_id = request_id_var.get()
        prefix = f"[{req_id[:8]}] " if req_id else ""
        record.msg = f"{prefix}{record.msg}"
        return super().format(record)


class RequestIdMiddleware(BaseHTTPMiddleware):
    """Middleware that assigns a unique request_id to each request."""

    async def dispatch(self, request: Request, call_next):
        req_id = request.headers.get("x-request-id") or str(uuid.uuid4())
        token = request_id_var.set(req_id)
        response = await call_next(request)
        response.headers["x-request-id"] = req_id
        request_id_var.reset(token)
        return response


def configure_logging(*, level: str = "INFO", json_logs: bool = False) -> None:
    """
    Configure process-wide logging.

    Uvicorn and Celery both use stdlib logging; configuring a consistent root handler
    makes logs predictable in containers (stdout/stderr).
    """
    root = logging.getLogger()
    if root.handlers:
        return

    handler = logging.StreamHandler(sys.stdout)
    handler.setLevel(level.upper())
    handler.setFormatter(
        _JsonFormatter()
        if json_logs
        else _TextFormatter(
            fmt="%(asctime)s %(levelname)s %(name)s - %(message)s",
        )
    )

    root.setLevel(level.upper())
    root.addHandler(handler)
