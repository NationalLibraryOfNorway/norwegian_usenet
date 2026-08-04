import logging
import mailbox
from pathlib import Path

import pandas as pd

from usenet_no.date_parsing import UNKNOWN_DATE, parse_and_normalize_date_field
from usenet_no.mbox_utils import (
    RawMessage,
    message_factory,
    split_envelope,
    unescape_from_lines,
    write_mbox,
)

logger = logging.getLogger(__name__)


def get_nb_date_span(date_count_csv: Path) -> tuple[str, str]:
    df = pd.read_csv(date_count_csv)
    dates = pd.to_datetime(df[df["date"] != UNKNOWN_DATE]["date"])
    return dates.min().strftime("%Y-%m-%d"), dates.max().strftime("%Y-%m-%d")


def filter_mbox_by_date(
    mbox_file: Path,
    output_file: Path,
    start_date: str,
    end_date: str,
    overwrite: bool = False,
) -> tuple[int, int]:
    """Copy messages from mbox_file to output_file, keeping only those within [start_date, end_date].
    Messages with unparseable dates are excluded.

    Returns (kept, total).
    """
    if output_file.exists() and not overwrite:
        kept = len(mailbox.mbox(str(output_file), factory=message_factory))
        total = len(mailbox.mbox(str(mbox_file), factory=message_factory))
        logger.info("%s: kept %d / %d (skipped)", mbox_file.name, kept, total)
        return kept, total

    mbox_in = mailbox.mbox(str(mbox_file), factory=message_factory)
    total = len(mbox_in)

    kept_texts = []
    for key, message in mbox_in.items():
        date_str = parse_and_normalize_date_field(message.get("Date", None))
        if (
            date_str != UNKNOWN_DATE and start_date <= date_str <= end_date
        ):  # ISO 8601 sorts lexicographically
            # mbox_file was written by write_mbox, so its envelope line is kept
            # and its "From " escaping is undone before it is written again.
            envelope, text = split_envelope(
                mbox_in.get_bytes(key, from_=True).decode("utf-8", errors="replace")
            )
            kept_texts.append(RawMessage(envelope, unescape_from_lines(text)))

    if not kept_texts:
        logger.info(
            "%s: kept 0 / %d (no messages in date range, skipping output)",
            mbox_file.name,
            total,
        )
        return 0, total

    write_mbox(kept_texts, output_file)
    logger.info("%s: kept %d / %d", mbox_file.name, len(kept_texts), total)
    return len(kept_texts), total
