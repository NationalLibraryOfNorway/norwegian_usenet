from datetime import datetime
from email.utils import parsedate_to_datetime
import logging

logger = logging.getLogger(__name__)


def parse_datestring(date_string: str) -> datetime | None:
    """Return a datetime object with year, month, day if parsing succeeds."""

    date_string = date_string.strip()
    if not date_string:
        return None

    # Try specific date formats seen in data, that are not supported by parsedate_to_datetime
    for fmt in ("%Y/%m/%d", "%d. %B %Y %H:%M"):
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
        return "unknown"
    parsed_date = parse_datestring(date_string=date_field)
    if parsed_date:
        return parsed_date.strftime("%Y-%m-%d")
    else:
        logger.warning("Date field: %s", date_field)
        return "unknown"
