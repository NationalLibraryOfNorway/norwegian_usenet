import argparse
import logging
from concurrent.futures import ProcessPoolExecutor, as_completed
from pathlib import Path

from tqdm import tqdm

from usenet_no.filter_internet_archive_by_date import (
    filter_mbox_by_date,
    get_nwa_date_span,
)

logger = logging.getLogger(__name__)


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
    parser.add_argument(
        "--overwrite",
        action="store_true",
        help="Re-filter and overwrite already existing output files instead of skipping",
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
                args.overwrite,
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
