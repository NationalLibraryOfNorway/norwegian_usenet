"""
Count message files whose Message-ID header holds bytes outside ASCII.

A check to run before hashing: the database hashes message ids from
chardet-decoded text, so an id with high bytes would hash to something else
if it were read as raw bytes instead.
"""

import argparse
import logging
from pathlib import Path

logger = logging.getLogger(__name__)


def message_id_line(message_file):
    """
    Takes a message file as input,
    reads the header block up to the first blank line,
    returns the raw Message-ID line as bytes, or None if there is none.
    """
    with message_file.open("rb") as file:
        for line in file:
            if not line.strip():
                return None
            if line.lower().startswith(b"message-id:"):
                return line
    return None


def count_source_dir(source_dir):
    """Read every message file below source_dir, returning the report lines for it."""
    lines = []
    files = missing = non_ascii = 0
    for message_file in source_dir.rglob("*"):
        if not message_file.is_file():
            continue
        files += 1
        line = message_id_line(message_file)
        if line is None:
            missing += 1
            lines.append(
                f"  no Message-ID: {message_file.relative_to(source_dir.parent)}"
            )
        elif any(byte > 127 for byte in line):
            non_ascii += 1
            lines.append(f"  non-ascii: {message_file.relative_to(source_dir.parent)}")
    lines.append(
        f"{source_dir.name}: {files} files, "
        f"{missing} without Message-ID, {non_ascii} with non-ascii Message-ID"
    )
    return lines


parser = argparse.ArgumentParser(
    description="Count NB message files whose Message-ID holds bytes outside ASCII",
    formatter_class=argparse.ArgumentDefaultsHelpFormatter,
)
parser.add_argument(
    "--unzipped-dir",
    type=Path,
    default=Path("data/input/nb/unzipped_data"),
    help="Directory holding the extracted NB sources, one message per file",
)
parser.add_argument(
    "--output-file",
    type=Path,
    default=Path(
        "data/output/01_extract_and_parse_usenet_data/non_ascii_nb_message_ids.txt"
    ),
    help="Text file to write the counts, and the path of every file reported, to",
)

args = parser.parse_args()
logging.basicConfig(level=logging.INFO)

report = []
for source_dir in sorted(d for d in args.unzipped_dir.glob("*") if d.is_dir()):
    for line in count_source_dir(source_dir):
        logger.info(line)
        report.append(line)

args.output_file.parent.mkdir(parents=True, exist_ok=True)
args.output_file.write_text("\n".join(report) + "\n", encoding="utf-8")
logger.info("Wrote %s", args.output_file)
