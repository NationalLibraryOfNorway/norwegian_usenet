import argparse
import logging
from pathlib import Path

from tqdm import tqdm

from usenet_no.archives.encoding import (
    FileEncodings,
    source_key,
    write_file_encodings,
)
from usenet_no.archives.parse_nb_archive import (
    build_mbox_files_from_single_message_textfiles,
    correct_stem,
    find_newsgroups_parent_dir,
    load_newsgroup_corrections,
)

logger = logging.getLogger(__name__)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Convert the extracted NB archives to utf-8 .mbox files",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument(
        "--unzipped-dir",
        type=Path,
        default=Path("data/input/nb/unzipped_data"),
        help="Directory containing the extracted NB sources (01_extract_nb_archive_and_find_stubbed_newsgroup_names.py)",
    )
    parser.add_argument(
        "--output-directory",
        type=Path,
        default=Path("data/input/nb/utf_8_data"),
        help="Directory to write generated .mbox files",
    )
    parser.add_argument(
        "--overwrite",
        action="store_true",
        help="Clear the output directory and regenerate all mbox files",
    )
    parser.add_argument(
        "--encodings-file",
        type=Path,
        default=Path("data/input/nb/encodings.json"),
        help="Path to JSON file storing the encoding detected per source message file",
    )
    parser.add_argument(
        "--newsgroup-corrections",
        type=Path,
        default=Path(
            "data/output/01_extract_and_parse_usenet_data/cut_off_newsgroup_names.csv"
        ),
        help="CSV mapping cut-off newsgroup names to their full names (01_extract_nb_archive_and_find_stubbed_newsgroup_names.py)",
    )
    args = parser.parse_args()
    logger.info("Args: %s", args)

    corrections = load_newsgroup_corrections(args.newsgroup_corrections)
    logger.info("Loaded %d newsgroup name corrections", len(corrections))

    # Every newsgroup is spread across the tar archives and appended to one mbox
    # file, so a run writes the whole output directory or none of it.
    args.output_directory.mkdir(exist_ok=True, parents=True)
    existing = list(args.output_directory.iterdir())
    if existing and not args.overwrite:
        parser.error(
            f"{args.output_directory} already holds {len(existing)} files;"
            " pass --overwrite to regenerate them"
        )
    for f in existing:
        f.unlink()
    if existing:
        logger.info("Cleared %d files from %s", len(existing), args.output_directory)

    encodings: FileEncodings = {}

    directories = sorted(d for d in args.unzipped_dir.iterdir() if d.is_dir())
    for directory in tqdm(directories, desc="Processing tar archives"):
        logger.info("Finding usenet data in %s", directory)

        # This function is needed because the newsgroups are nested differently depending on which CD the data was stored on
        newsgroups_parent_dir = find_newsgroups_parent_dir(directory)
        logger.info("Newsgroups parent directory: %s", newsgroups_parent_dir)

        for newsgroup_dir in sorted(newsgroups_parent_dir.iterdir()):
            if not newsgroup_dir.is_dir():
                continue
            stem = correct_stem(f"no.{newsgroup_dir.name.lower()}", corrections)
            detected = build_mbox_files_from_single_message_textfiles(
                newsgroup_dir=newsgroup_dir,
                outfile=args.output_directory / f"{stem}.mbox",
                corrections=corrections,
            )
            encodings.update(
                {
                    source_key(message_file, args.unzipped_dir): encoding
                    for message_file, encoding in detected.items()
                }
            )

    write_file_encodings(encodings, args.encodings_file)
