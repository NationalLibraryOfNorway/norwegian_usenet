"""Package initialization for usenet_no."""

import logging
import os

DEFAULT_LEVEL = logging.INFO


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
    logging.basicConfig(level=level)


_setup_logging()
