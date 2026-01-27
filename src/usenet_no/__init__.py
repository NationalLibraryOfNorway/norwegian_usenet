"""Package initialization for usenet_no."""

import logging
import os
from datetime import datetime
from pathlib import Path

DEFAULT_LEVEL = logging.INFO
LOG_DIR = Path(__file__).resolve().parents[2] / "logs"
LOG_FILE_PATH = LOG_DIR / f"{datetime.now().strftime('%Y%m%d-%H%M%S')}.log"


def _resolve_log_level(env_level: str) -> int:
    """Resolve an environment-provided log level, defaulting to INFO."""

    candidate = env_level.strip()

    if candidate.isdigit():
        return int(candidate)

    level_map = logging.getLevelNamesMapping()
    mapped = level_map.get(candidate.upper())
    return mapped if isinstance(mapped, int) else DEFAULT_LEVEL


def _setup_logging() -> None:
    """Configure root logging from LOG_LEVEL env var once on import."""
    level = DEFAULT_LEVEL

    env_level = os.getenv("LOG_LEVEL", None)

    if env_level:
        level = _resolve_log_level(env_level)

    LOG_DIR.mkdir(parents=True, exist_ok=True)

    handlers = [
        logging.StreamHandler(),
        logging.FileHandler(str(LOG_FILE_PATH), encoding="utf-8"),
    ]

    logging.basicConfig(
        level=level,
        handlers=handlers,
        format="%(asctime)s %(name)s [%(levelname)s] %(message)s",
        force=True,
    )


_setup_logging()
