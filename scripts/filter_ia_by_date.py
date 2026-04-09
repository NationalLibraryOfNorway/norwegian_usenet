import argparse
import logging
import mailbox
from concurrent.futures import ProcessPoolExecutor, as_completed
from pathlib import Path

import pandas as pd
from tqdm import tqdm

from usenet_no.date_parsing import parse_and_normalize_date_field
from usenet_no.mbox_utils import ensure_mbox_envelope, message_factory

logger = logging.getLogger(__name__)


def get_nwa_date_span(date_count_csv: Path) -> tuple[str, str]:
    df = pd.read_csv(date_count_csv)
    dates = pd.to_datetime(df[df["date"] != "unknown"]["date"])
    return dates.min().strftime("%Y-%m-%d"), dates.max().strftime("%Y-%m-%d")


def filter_mbox_by_date(
    mbox_file: Path,
    output_file: Path,
    start_date: str,
    end_date: str,
) -> tuple[int, int]:
    """Copy messages from mbox_file to output_file, keeping only those within [start_date, end_date].
    Messages with unparseable dates are always kept.

    Returns (kept, total).
    """
    if output_file.exists():
        kept = len(mailbox.mbox(str(output_file)))
        total = len(mailbox.mbox(str(mbox_file)))
        logger.info("%s: kept %d / %d (skipped)", mbox_file.name, kept, total)
        return kept, total

    mbox_in = mailbox.mbox(str(mbox_file), factory=message_factory)
    keys = list(mbox_in.keys())

    tmp_file = output_file.with_suffix(".tmp")
    kept = 0
    with tmp_file.open("wb") as f:
        for key in keys:
            message = mbox_in[key]
            date_str = parse_and_normalize_date_field(message.get("Date", None))
            if (
                date_str == "unknown" or start_date <= date_str <= end_date
            ):  # ISO 8601 sorts lexicographically
                text = mbox_in.get_bytes(key).decode("utf-8", errors="replace")
                f.write(ensure_mbox_envelope(text).encode("utf-8"))
                kept += 1
    if kept:
        tmp_file.rename(output_file)
    else:
        tmp_file.unlink()
    logger.info("%s: kept %d / %d", mbox_file.name, kept, len(keys))
    return kept, len(keys)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Filter IA mbox files to the date span of the NWA archive"
    )
    parser.add_argument(
        "--ia-directory",
        type=Path,
        default=Path("data/internet_archive/utf_8_data"),
        help="Directory containing IA mbox files",
    )
    parser.add_argument(
        "--nwa-date-csv",
        type=Path,
        default=Path("data/date_count_nwa.csv"),
        help="CSV with date counts for the NWA archive",
    )
    parser.add_argument(
        "--output-directory",
        type=Path,
        default=Path("data/internet_archive/date_filtered"),
        help="Directory to write filtered mbox files",
    )
    args = parser.parse_args()

    start_date, end_date = get_nwa_date_span(args.nwa_date_csv)
    logger.info("NWA date span: %s to %s", start_date, end_date)
    print(f"NWA date span: {start_date} to {end_date}")

    args.output_directory.mkdir(parents=True, exist_ok=True)

    mbox_files = sorted(args.ia_directory.glob("*.mbox"))
    total_kept = 0
    total_msgs = 0

    with ProcessPoolExecutor() as executor:
        futures = {
            executor.submit(
                filter_mbox_by_date,
                mbox_file,
                args.output_directory / mbox_file.name,
                start_date,
                end_date,
            ): mbox_file
            for mbox_file in mbox_files
        }
        for future in tqdm(
            as_completed(futures), total=len(futures), desc="Filtering mbox files"
        ):
            kept, total = future.result()
            total_kept += kept
            total_msgs += total

    print(f"Done. Kept {total_kept:,} / {total_msgs:,} messages total.")
