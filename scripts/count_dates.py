import argparse
import logging
from collections import Counter
from pathlib import Path

import pandas as pd
from tqdm import tqdm

from usenet_no.mbox_utils import get_messages_date_field
from usenet_no.date_parsing import parse_and_normalize_date_field

logger = logging.getLogger(__name__)


def count_dates_in_mbox_file(mbox_file: Path, date_counts: Counter[str]) -> None:
    """
    Reads messages in mbox_file and increments the counter for each Date header.
    """
    for date_field in get_messages_date_field(mbox_file=mbox_file):
        counts_key = parse_and_normalize_date_field(date_field=date_field)
        date_counts[counts_key] += 1


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Count messages per Date header")
    parser.add_argument(
        "--directory",
        "-d",
        type=Path,
        default=Path("data/utf_8_data"),
        help="Directory containing .mbox files",
    )
    parser.add_argument(
        "--output-file",
        "-o",
        type=Path,
        default=Path("data/date_count.csv"),
        help="Path to CSV output file",
    )
    parser.add_argument(
        "--overwrite",
        action="store_true",
        help="If flagged, will overwrite existing files instead of skipping",
    )
    parser.add_argument(
        "--limit",
        type=int,
        metavar="N",
        default=None,
        help="If passed, will only count messages for the first N mbox files",
    )

    args = parser.parse_args()
    logger.info("Args: %s", args)

    if args.output_file.exists() and not args.overwrite:
        logger.info(
            "Existing file found at %s; use --overwrite to regenerate", args.output_file
        )
        exit(0)

    date_counts: Counter[str] = Counter()
    mbox_files = sorted(args.directory.glob("*.mbox"))

    for index, mbox_file in enumerate(
        tqdm(mbox_files, total=args.limit or len(mbox_files))
    ):
        if index == args.limit:
            break
        count_dates_in_mbox_file(mbox_file, date_counts)
        logger.debug("Processed %s", mbox_file.name)
        df = pd.DataFrame(date_counts.items(), columns=["date", "count"])
        df.to_csv(args.output_file, index=False)

    logger.info("Total dates counted: %d", sum(date_counts.values()))
