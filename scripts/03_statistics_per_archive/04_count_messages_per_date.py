import argparse
import logging
from collections import Counter
from concurrent.futures import ProcessPoolExecutor, as_completed
from pathlib import Path

import pandas as pd
from tqdm import tqdm

from usenet_no.mbox_utils import get_messages_date_field
from usenet_no.date_parsing import parse_and_normalize_date_field

logger = logging.getLogger(__name__)


def count_dates_in_mbox_file(mbox_file: Path) -> Counter[str]:
    counts: Counter[str] = Counter()
    for date_field in get_messages_date_field(mbox_file=mbox_file):
        counts[parse_and_normalize_date_field(date_field=date_field)] += 1
    return counts


def count_dates_parallel(mbox_files: list[Path]) -> dict[str, int]:
    """Parse Date header of every message in every mbox file and return the date count across all files"""
    date_counts: Counter[str] = Counter()

    with ProcessPoolExecutor() as executor:
        futures = {executor.submit(count_dates_in_mbox_file, f): f for f in mbox_files}
        for future in tqdm(
            as_completed(futures), total=len(mbox_files), desc="Counting dates"
        ):
            date_counts += future.result()

    return date_counts


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Parse date fields in messages Date header for all messages in both archives"
    )
    parser.add_argument(
        "--ia-directory",
        type=Path,
        default=Path("data/internet_archive/utf_8_data"),
        help="Directory containing Internet Archive (IA) .mbox files",
    )
    parser.add_argument(
        "--nb-directory",
        type=Path,
        default=Path("data/nb/utf_8_data"),
        help="Directory containing Nasjonalbiblioteket (NB) .mbox files",
    )
    parser.add_argument(
        "--ia-output-file",
        type=Path,
        default=Path("data/date_count_ia.csv"),
        help="Path to CSV output file for IA date counts",
    )
    parser.add_argument(
        "--nb-output-file",
        type=Path,
        default=Path("data/date_count_nb.csv"),
        help="Path to CSV output file for NB date counts",
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

    for directory, output_file in [
        (args.ia_directory, args.ia_output_file),
        (args.nb_directory, args.nb_output_file),
    ]:
        if output_file.exists() and not args.overwrite:
            logger.info(
                "Existing file found at %s; use --overwrite to regenerate",
                output_file,
            )
            continue

        mbox_files = sorted(directory.glob("*.mbox"))[: args.limit]

        date_counts = count_dates_parallel(mbox_files=mbox_files)

        df = pd.DataFrame(date_counts.items(), columns=["date", "count"]).sort_values(
            "date"
        )

        df.to_csv(output_file, index=False)
        logger.info(
            "Counted %d dates in %s. Saved date counts to %s",
            sum(date_counts.values()),
            directory,
            output_file,
        )
