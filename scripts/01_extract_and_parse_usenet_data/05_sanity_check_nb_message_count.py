"""Check that the NB mbox files hold as many messages as they were written from.

The NB sources hold one message per file, so counting the files gives a message
count that owes nothing to reading an mbox file. This replays the traversal
02_parse_nb_archive.py performs to find the source files behind each mbox file,
and compares that count against the messages the mbox file reads as.

Exits non-zero when the two disagree.
"""

import argparse
import logging
from pathlib import Path

from tqdm import tqdm

from usenet_no.archives.parse_nb_archive import (
    count_source_files_per_newsgroup,
    load_newsgroup_corrections,
)
from usenet_no.mbox_utils import open_mbox

logger = logging.getLogger(__name__)


def count_messages(mbox_file: Path) -> int:
    """The number of messages the mbox file reads as, or 0 when there is no such file."""
    if not mbox_file.exists():
        logger.warning("No mbox file at %s", mbox_file)
        return 0
    return len(open_mbox(mbox_file))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Check the NB mbox message counts against the source file counts",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument(
        "--unzipped-dir",
        type=Path,
        default=Path("data/input/nb/unzipped_data"),
        help="Directory holding the extracted NB sources, one message per file",
    )
    parser.add_argument(
        "--mbox-directory",
        type=Path,
        default=Path("data/input/nb/utf_8_data"),
        help="Directory holding the .mbox files written by 02_parse_nb_archive.py",
    )
    parser.add_argument(
        "--newsgroup-corrections",
        type=Path,
        default=Path(
            "data/output/01_extract_and_parse_usenet_data/cut_off_newsgroup_names.csv"
        ),
        help="CSV mapping cut-off newsgroup names to their full names, as used by the parse",
    )

    args = parser.parse_args()
    logging.basicConfig(level=logging.INFO)
    logger.info("Args: %s", args)

    corrections = load_newsgroup_corrections(args.newsgroup_corrections)
    source_files = count_source_files_per_newsgroup(args.unzipped_dir, corrections)

    differing = []
    total_sources = total_messages = 0
    for stem in tqdm(sorted(source_files), desc="Comparing newsgroups"):
        expected = source_files[stem]
        found = count_messages(args.mbox_directory / f"{stem}.mbox")
        total_sources += expected
        total_messages += found
        if found != expected:
            differing.append((stem, expected, found))

    logger.info("Source files: %d", total_sources)
    logger.info("Messages in the mbox files: %d", total_messages)

    if not differing:
        logger.info("Every one of the %d newsgroups matches", len(source_files))
        raise SystemExit(0)

    for stem, expected, found in differing:
        logger.error(
            "%s: %d source files, %d messages (%+d)",
            stem,
            expected,
            found,
            found - expected,
        )
    logger.error(
        "%d of %d newsgroups differ, %+d messages in total",
        len(differing),
        len(source_files),
        total_messages - total_sources,
    )
    raise SystemExit(1)
