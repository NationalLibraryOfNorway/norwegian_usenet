import logging
import re
from datetime import datetime
from email.utils import parsedate_to_datetime

logger = logging.getLogger(__name__)

# What parse_and_normalize_date_field returns for a date it cannot parse.
UNKNOWN_DATE = "unknown"


def _fix_invalid_timezone(date_string: str) -> str:
    """Replace timezone offsets with hour > 14 (invalid) with +0000."""
    match = re.search(r"([+-])(\d{2})\d{2}$", date_string)
    if match and int(match.group(2)) > 14:
        return date_string[: match.start()] + "+0000"
    return date_string


def parse_datestring(date_string: str) -> datetime | None:
    """Return a datetime object with year, month, day if parsing succeeds."""

    date_string = date_string.strip()
    if not date_string:
        return None

    # Fix malformed seconds like "23:37: 7" → "23:37:07"
    date_string = re.sub(r":\s(\d)\b", r":0\1", date_string)

    # Fix invalid timezone offsets
    date_string = _fix_invalid_timezone(date_string)

    # Try specific date formats seen in data, that are not supported by parsedate_to_datetime
    for fmt in (
        "%Y/%m/%d",
        "%d. %B %Y %H:%M",
        "%d %b %Y",
        "%d %b %y %H:%M:%S %Z",
        "%d %b %Y %H:%M:%S %z",
    ):
        try:
            parsed = datetime.strptime(date_string, fmt)
            return datetime(parsed.year, parsed.month, parsed.day)
        except ValueError:
            continue

    try:
        parsed = parsedate_to_datetime(date_string)
        return datetime(parsed.year, parsed.month, parsed.day)

    except (TypeError, ValueError):
        logger.debug("Could not parse date from string :%s", date_string)
        return None


def parse_and_normalize_date_field(date_field: str | None) -> str:
    if date_field is None:
        return UNKNOWN_DATE
    parsed_date = parse_datestring(date_string=date_field)
    if parsed_date:
        return parsed_date.strftime("%Y-%m-%d")
    else:
        logger.warning("Date field: %s", date_field)
        return UNKNOWN_DATE
