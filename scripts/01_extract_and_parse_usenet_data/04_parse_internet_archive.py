import argparse
import logging
from concurrent.futures import ProcessPoolExecutor, as_completed
from pathlib import Path
from zipfile import ZipFile

from tqdm import tqdm

from usenet_no.archives.encoding import (
    FileEncodings,
    load_file_encodings,
    source_key,
    write_file_encodings,
)
from usenet_no.archives.parse_internet_archive import process_mbox_file

logger = logging.getLogger(__name__)


def unzip_all(zip_dir: Path, unzip_dir: Path) -> None:
    all_zips = list(zip_dir.glob("*.zip"))
    for zip_file in tqdm(all_zips, desc="Unzipping zipped mbox files"):
        with ZipFile(zip_file, "r") as z:
            z.extractall(unzip_dir)
        logger.debug("Extracted archive %s into %s", zip_file.name, unzip_dir)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Unzip and parse Usenet mbox data to utf-8 readable format",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument(
        "--zipped-data-dir",
        type=Path,
        default=Path("data/input/internet_archive/zipped_data"),
        help="Directory containing zipped mbox files",
    )
    parser.add_argument(
        "--unzipped-data-dir",
        type=Path,
        default=Path("data/input/internet_archive/unzipped_data"),
        help="Directory to store unzipped mbox files",
    )
    parser.add_argument(
        "--decoded-data-dir",
        type=Path,
        default=Path("data/input/internet_archive/utf_8_data"),
        help="Directory to store utf-8 encoded unzipped mbox files",
    )
    parser.add_argument(
        "--encodings-file",
        type=Path,
        default=Path("data/input/internet_archive/encodings.json"),
        help="Path to JSON file storing the encoding detected per source mbox file",
    )
    parser.add_argument(
        "--overwrite",
        action="store_true",
        help="If flagged, will overwrite existing files instead of skipping",
    )
    args = parser.parse_args()
    logger.info("args %s", args)

    args.unzipped_data_dir.mkdir(exist_ok=True)
    args.decoded_data_dir.mkdir(exist_ok=True)

    num_docs_zipped = len(list(args.zipped_data_dir.iterdir()))
    num_docs_unzipped = len(list(args.unzipped_data_dir.iterdir()))
    logger.info(
        "Number of zipped files: %d | Number of unzipped files: %d",
        num_docs_zipped,
        num_docs_unzipped,
    )
    if num_docs_zipped != num_docs_unzipped:
        unzip_all(args.zipped_data_dir, args.unzipped_data_dir)

    encodings: FileEncodings = (
        {} if args.overwrite else load_file_encodings(args.encodings_file)
    )

    unzipped_mbox_files = [
        f
        for f in args.unzipped_data_dir.iterdir()
        if not (
            source_key(f, args.unzipped_data_dir) in encodings
            and (args.decoded_data_dir / f.name).exists()
            and not args.overwrite
        )
    ]

    with ProcessPoolExecutor() as executor:
        futures = {
            executor.submit(
                process_mbox_file,
                mbox_file,
                args.decoded_data_dir / mbox_file.name,
            ): mbox_file
            for mbox_file in unzipped_mbox_files
        }
        for future in tqdm(
            as_completed(futures),
            total=len(futures),
            desc=f"Parsing mbox files to {args.decoded_data_dir}",
        ):
            mbox_file = futures[future]
            encodings[source_key(mbox_file, args.unzipped_data_dir)] = future.result()

    write_file_encodings(encodings, args.encodings_file)
