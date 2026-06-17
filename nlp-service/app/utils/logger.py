import logging
import json
import sys
from contextvars import ContextVar

from app.config import settings

# Context variable for request-scoped request_id
_request_id_ctx: ContextVar[str] = ContextVar("request_id", default="")


def set_request_id(request_id: str) -> None:
    """Set the request_id for the current async context."""
    _request_id_ctx.set(request_id)


def get_request_id() -> str:
    """Get the request_id for the current async context."""
    return _request_id_ctx.get("")


class JsonFormatter(logging.Formatter):
    def format(self, record):
        log_data = {
            "timestamp": self.formatTime(record),
            "level": record.levelname,
            "service": "nlp-service",
            "message": record.getMessage(),
            "module": record.module,
        }
        if record.exc_info and record.exc_info[0]:
            log_data["exception"] = self.formatException(record.exc_info)

        # request_id: prefer explicit extra, then context var
        rid = getattr(record, "request_id", None) or get_request_id()
        if rid:
            log_data["request_id"] = rid

        return json.dumps(log_data)


_LOG_LEVEL_MAP = {
    "debug": logging.DEBUG,
    "info": logging.INFO,
    "warning": logging.WARNING,
    "error": logging.ERROR,
    "critical": logging.CRITICAL,
}


def get_logger(name: str) -> logging.Logger:
    logger = logging.getLogger(name)
    if not logger.handlers:
        handler = logging.StreamHandler(sys.stdout)
        handler.setFormatter(JsonFormatter())
        logger.addHandler(handler)
        level = _LOG_LEVEL_MAP.get(settings.log_level.lower(), logging.INFO)
        logger.setLevel(level)
    return logger
