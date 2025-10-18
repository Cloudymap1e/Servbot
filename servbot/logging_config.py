"""Central logging configuration with redaction and rotation."""
from __future__ import annotations

import logging
import logging.handlers
from pathlib import Path
from typing import Optional

from .secure_store import setup_logging_redaction


DEFAULT_LOG_DIR = Path(__file__).resolve().parents[1] / "logs"
DEFAULT_LOG_FILE = DEFAULT_LOG_DIR / "servbot.log"


def setup_logging(debug: bool = False, log_file: Optional[str] = None) -> None:
    """Configure logging with console + rotating file handlers and redaction.

    Args:
        debug: Enable DEBUG level
        log_file: Path to log file (defaults to logs/servbot.log)
    """
    DEFAULT_LOG_DIR.mkdir(parents=True, exist_ok=True)
    logfile = Path(log_file) if log_file else DEFAULT_LOG_FILE

    level = logging.DEBUG if debug else logging.INFO
    logger = logging.getLogger()
    logger.setLevel(level)

    # Console handler
    ch = logging.StreamHandler()
    ch.setLevel(level)
    ch.setFormatter(logging.Formatter('%(asctime)s [%(levelname)s] %(name)s: %(message)s'))

    # Rotating file handler
    fh = logging.handlers.RotatingFileHandler(str(logfile), maxBytes=5_000_000, backupCount=5, encoding='utf-8')
    fh.setLevel(level)
    fh.setFormatter(logging.Formatter('%(asctime)s [%(levelname)s] %(name)s (%(filename)s:%(lineno)d): %(message)s'))

    # Clear existing handlers to avoid duplicates
    logger.handlers = []
    logger.addHandler(ch)
    logger.addHandler(fh)

    # Add redaction filter
    setup_logging_redaction()

    logging.getLogger(__name__).info("Logging initialized. File: %s", logfile)
