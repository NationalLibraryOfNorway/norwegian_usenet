"""Print the part of an NB mbox file that one source message file was written to.

The NB sources hold one message per file, and the parse appends them to their
newsgroup's mbox file in a fixed order, so a source file's place in that order
is the message's position in the mbox file. Takes the path of a source file
below --unzipped-dir and prints the message at that position, envelope line and
all, as the mbox file holds it.
"""

import argparse
import logging
from pathlib import Path

from usenet_no.archives.parse_nb_archive import (
    collect_source_files_per_newsgroup,
    load_newsgroup_corrections,
)
from usenet_no.mbox_utils import StrictMbox, get_message_body, open_mbox

logger = logging.getLogger(__name__)


def find_message_position(
    message_file: Path, sources: dict[str, list[Path]]
) -> tuple[str, int]:
    """The mbox file stem the source file was written to, and its position in that file."""
    for stem, message_files in sources.items():
        if message_file in message_files:
            return stem, message_files.index(message_file)


def read_raw_message(mbox: StrictMbox, position: int) -> bytes:
    """The bytes of the message at the 0-based position, headers and body as stored."""
    return mbox.get_bytes(position)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Print the mbox file part that one NB source message file was written to",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument(
        "message_file",
        type=Path,
        help="Path of a source message file below --unzipped-dir",
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

    corrections = load_newsgroup_corrections(args.newsgroup_corrections)

    # Resolved, so the collected paths compare equal to the argument's own path
    sources = collect_source_files_per_newsgroup(
        args.unzipped_dir.resolve(), corrections
    )
    stem, position = find_message_position(args.message_file.resolve(), sources)

    mbox_file = args.mbox_directory / f"{stem}.mbox"
    mbox = open_mbox(mbox_file)
    logger.info("%s, message %d of %d", mbox_file, position, len(sources[stem]))
    logger.info("---file content---")
    print(read_raw_message(mbox, position).decode("utf-8"))
    # What the analysis reads the message as: every run of whitespace collapsed
    logger.info("--- text from get_message_body---")
    print(get_message_body(mbox[position]))
