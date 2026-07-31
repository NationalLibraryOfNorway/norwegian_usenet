import argparse
import logging
import time
from pathlib import Path

from tqdm import tqdm

from usenet_no.archives.scrape_internet_archive import (
    download_zip,
    get_page_data,
    get_urls,
)

logger = logging.getLogger(__name__)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Download Usenet archives",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument(
        "--page-data",
        type=Path,
        default=Path("data/output/01_extract_and_parse_usenet_data/page_data.txt"),
        help="Location of cached page HTML",
    )
    parser.add_argument(
        "--base-url",
        default="https://archive.org/download/usenet-no",
        help="Usenet archive base URL",
    )
    parser.add_argument(
        "--data-dir",
        type=Path,
        default=Path("data/input/internet_archive/zipped_data"),
        help="Directory where zip files are stored",
    )
    parser.add_argument(
        "--overwrite",
        action="store_true",
        help="Force re-download of already downloaded files",
    )
    parser.add_argument(
        "--retry-count",
        type=int,
        default=5,
        help="Number of retries per file download",
    )
    args = parser.parse_args()

    args.data_dir.mkdir(parents=True, exist_ok=True)

    page_data = get_page_data(
        page_url=args.base_url,
        page_data_file=args.page_data,
        download_again=args.overwrite,
    )
    urls = get_urls(page_data)

    failed = []

    for filename in tqdm(sorted(urls)):
        zip_url = f"{args.base_url}/{filename}"
        local_file = args.data_dir / filename

        if local_file.exists() and not args.overwrite:
            continue

        logger.info("FILENAME: %r", filename)
        logger.info("ZIP URL:  %s", zip_url)

        try:
            download_zip(zip_url, local_filename=local_file, retries=args.retry_count)
            time.sleep(0.5)
        except Exception as e:
            logger.error("FAILED: %s -> %s", filename, e)
            failed.append(filename)

    if failed:
        failed_file = args.data_dir.parent / "failed_downloads.txt"
        failed_file.write_text("\n".join(failed) + "\n")
        logger.info("Saved failed downloads to %s", failed_file)
        logger.info("Failed downloads: %d", len(failed))
    else:
        logger.info("All downloads completed successfully.")
