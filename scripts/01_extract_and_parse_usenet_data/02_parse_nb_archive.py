import argparse
import logging
from pathlib import Path

from tqdm import tqdm

from usenet_no.parse_norwegian_web_archive import (
    concat_textfiles,
    correct_stem,
    find_newsgroups_parent_dir,
    load_newsgroup_corrections,
)

logger = logging.getLogger(__name__)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Convert the extracted NB archives to utf-8 .mbox files"
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
        help="Clear output directory and regenerate all mbox files instead of skipping existing",
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

    args.output_directory.mkdir(exist_ok=True, parents=True)
    if args.overwrite:
        for f in args.output_directory.iterdir():
            f.unlink()
        logger.info("Cleared output directory %s", args.output_directory)

    pre_existing = {f.name for f in args.output_directory.iterdir()}

    directories = [d for d in args.unzipped_dir.iterdir() if d.is_dir()]
    for directory in tqdm(directories, desc="Processing tar archives"):
        logger.info("Finding usenet data in %s", directory)

        # This function is needed because the newsgroups are nested differently depending on which CD the data was stored on
        newsgroups_parent_dir = find_newsgroups_parent_dir(directory)
        logger.info("Newsgroups parent directory: %s", newsgroups_parent_dir)

        for newsgroup_dir in sorted(newsgroups_parent_dir.iterdir()):
            if not newsgroup_dir.is_dir():
                continue
            stem = correct_stem(f"no.{newsgroup_dir.name.lower()}", corrections)
            concat_textfiles(
                newsgroup_dir=newsgroup_dir,
                outfile=args.output_directory / f"{stem}.mbox",
                pre_existing=pre_existing,
                corrections=corrections,
            )
