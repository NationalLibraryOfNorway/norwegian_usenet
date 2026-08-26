"""
Count message files whose Message-ID header holds bytes outside ASCII.

A check to run before hashing: the database hashes message ids from
chardet-decoded text, so an id with high bytes would hash to something else
if it were read as raw bytes instead.
"""

import sys
from pathlib import Path

ORIGINAL_DATA_DIR = Path(
    sys.argv[1] if len(sys.argv) > 1 else "data/input/nb/unzipped_data"
)


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


for source_dir in sorted(d for d in ORIGINAL_DATA_DIR.glob("*") if d.is_dir()):
    files = missing = non_ascii = 0
    for message_file in source_dir.rglob("*"):
        if not message_file.is_file():
            continue
        files += 1
        line = message_id_line(message_file)
        if line is None:
            missing += 1
        elif any(byte > 127 for byte in line):
            non_ascii += 1
            print(f"  non-ascii: {message_file.relative_to(source_dir)}")
    print(
        f"{source_dir.name}: {files} files, "
        f"{missing} without Message-ID, {non_ascii} with non-ascii Message-ID"
    )