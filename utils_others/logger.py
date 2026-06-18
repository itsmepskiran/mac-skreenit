import logging
import sys
from logging.handlers import RotatingFileHandler
import os
import json
import contextvars  # 
from datetime import datetime
import multiprocessing

# 
request_id_context = contextvars.ContextVar("request_id", default=None)

# ---------------------------------------------------------
# JSON Log Formatter
# ---------------------------------------------------------
class JSONFormatter(logging.Formatter):
    def format(self, record):
        log_record = {
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "level": record.levelname,
            "message": record.getMessage(),
            "logger": record.name,
            "module": record.module,
            "function": record.funcName,
            "line": record.lineno,
            "environment": os.getenv("ENVIRONMENT", "development"),
            "pid": os.getpid(),
            "thread": record.thread,
        }

        # Request metadata
        # "request_id" is special because we might grab it from context
        request_id = getattr(record, "request_id", None)
        if request_id is not None:
            log_record["request_id"] = request_id

        # Other fields (only if explicitly passed in extra={})
        for field in ["request_path", "request_method", "user_id", "role", "ip"]:
            if hasattr(record, field):
                log_record[field] = getattr(record, field)

        # Exception details
        if record.exc_info:
            log_record["exception"] = self.formatException(record.exc_info)

        return json.dumps(log_record)


# ---------------------------------------------------------
# Filter to ensure request_id always exists
# ---------------------------------------------------------
class RequestIDFilter(logging.Filter):
    def filter(self, record):
        # 1. Check if it was passed explicitly (logger.info(..., extra={"request_id": "..."}))
        if not hasattr(record, "request_id"):
            # 2. If not, try to grab it from the ContextVar
            ctx_id = request_id_context.get()
            record.request_id = ctx_id if ctx_id else None
            
        return True


# ---------------------------------------------------------
# Logger Setup
# ---------------------------------------------------------
def setup_logging():
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))
    log_dir = os.path.abspath(os.path.join(BASE_DIR, "..", "..", "logs"))
    os.makedirs(log_dir, exist_ok=True)

    logger = logging.getLogger()
    log_level = os.getenv("LOG_LEVEL", "INFO").upper()
    logger.setLevel(log_level)

    formatter = JSONFormatter()

    # Remove existing handlers
    for handler in list(logger.handlers):
        logger.removeHandler(handler)

    # Console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(formatter)
    console_handler.addFilter(RequestIDFilter())
    logger.addHandler(console_handler)

    # File handler - only in main process to avoid Windows permission conflicts
    # when uvicorn subprocesses try to access the same log file during shutdown
    is_main_process = multiprocessing.parent_process() is None
    if is_main_process and os.getenv("ENVIRONMENT", "development") != "production":
        file_handler = RotatingFileHandler(
            os.path.join(log_dir, "app.log"),
            maxBytes=10 * 1024 * 1024,
            backupCount=5
        )
        file_handler.setFormatter(formatter)
        file_handler.addFilter(RequestIDFilter())
        logger.addHandler(file_handler)

    # Sync Uvicorn + FastAPI logs
    for name in ["uvicorn", "uvicorn.error", "fastapi"]:
        uvicorn_logger = logging.getLogger(name)
        uvicorn_logger.handlers = logger.handlers
        uvicorn_logger.setLevel(logger.level)
        uvicorn_logger.propagate = False

    return logger


logger = setup_logging()