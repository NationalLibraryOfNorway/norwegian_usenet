from zipfile import ZipFile
from pathlib import Path

from mailbox import mbox
import argparse
import cchardet as chardet
from tqdm import tqdm
import json
import logging


logger = logging.getLogger(__name__)


def unzip_all(zip_dir: Path, unzip_dir: Path) -> None:
    all_zips = list(zip_dir.glob("*.zip"))
    for zip_file in tqdm(all_zips, desc="Unzipping zipped mbox files"):
        with ZipFile(zip_file, "r") as z:
            z.extractall(unzip_dir)
        logger.debug("Extracted archive %s into %s", zip_file.name, unzip_dir)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Unzip and parse Usenet mbox data to utf-8 readable format"
    )
    parser.add_argument(
        "--zipped-data-dir",
        type=Path,
        default=Path("data/internet_archive/zipped_data"),
        help="Directory containing zipped mbox files",
    )
    parser.add_argument(
        "--unzipped-data-dir",
        type=Path,
        default=Path("data/internet_archive/unzipped_data"),
        help="Directory to store unzipped mbox files",
    )
    parser.add_argument(
        "--decoded-data-dir",
        type=Path,
        default=Path("data/internet_archive/utf_8_data"),
        help="Directory to store utf-8 encoded unzipped mbox files",
    )
    parser.add_argument(
        "--encodings-file",
        type=Path,
        default=Path("data/internet_archive/encodings.json"),
        help="Path to JSON file storing detected encodings",
    )
    parser.add_argument(
        "--unicode-error-handler",
        default="backslashreplace",
        help="Error handling strategy for UnicodeDecodeError",
    )
    parser.add_argument(
        "--overwrite",
        action="store_true",
        help="If flagged, will overwrite existing files (encodings-file and mbox files in decoded-data-dir) instead of skipping",
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
        num_docs_zipped,
    )
    if num_docs_zipped != num_docs_unzipped:
        unzip_all(args.zipped_data_dir, args.unzipped_data_dir)

    if args.encodings_file.exists() and not args.overwrite:
        files_encodings = json.load(args.encodings_file.open())
    else:
        files_encodings = {}

    unzipped_mbox_files = list(args.unzipped_data_dir.iterdir())

    for mbox_file in tqdm(
        unzipped_mbox_files,
        desc=f"Reading each mbox file and write with utf-8 encoding to {args.decoded_data_dir}",
    ):
        outfile = args.decoded_data_dir / mbox_file.name

        if (
            mbox_file.stem in files_encodings
            and outfile.exists()
            and not args.overwrite
        ):
            continue
        try:
            # If messages can be iterated over by default, there are no encoding issues
            [e for e in mbox(mbox_file)]
            files_encodings[mbox_file.stem] = {"encoding": "utf-8"}
            outfile.write_bytes(mbox_file.read_bytes())
            logger.debug(
                "Copied UTF-8 mbox file %s without re-encoding", mbox_file.name
            )

        except UnicodeDecodeError:
            detection = chardet.detect(mbox_file.read_bytes())
            files_encodings[mbox_file.stem] = detection
            encoding = detection.get("encoding")
            text = mbox_file.read_bytes().decode(
                encoding, errors=args.unicode_error_handler
            )
            outfile.write_text(text, encoding="utf-8")
            logger.debug(
                "Re-encoded %s from %s to UTF-8",
                mbox_file.name,
                encoding,
            )

    with args.encodings_file.open("w+") as f:
        json.dump(files_encodings, fp=f, indent=4)
    logger.info(
        "Wrote encodings metadata for %d files to %s",
        len(files_encodings),
        args.encodings_file,
    )
