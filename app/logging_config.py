import json
import logging
import sys
from datetime import UTC, datetime
from typing import Any


class _JsonFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        payload: dict[str, Any] = {
            "ts": datetime.now(UTC).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }
        if record.exc_info:
            payload["exc_info"] = self.formatException(record.exc_info)
        if record.stack_info:
            payload["stack_info"] = record.stack_info
        return json.dumps(payload, ensure_ascii=False)


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
        else logging.Formatter(
            fmt="%(asctime)s %(levelname)s %(name)s - %(message)s",
        )
    )

    root.setLevel(level.upper())
    root.addHandler(handler)
