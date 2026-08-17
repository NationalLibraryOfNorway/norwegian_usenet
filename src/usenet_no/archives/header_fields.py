"""Count the message header fields the archive sources carry.

The NB sources hold one message per file and the IA sources one mbox file per
newsgroup, so each archive has its own way of reading header blocks out of them;
the counting and the file written are shared.
"""

import csv
import logging
import re
from collections import Counter, defaultdict
from collections.abc import Iterable, Iterator
from dataclasses import dataclass
from email.parser import HeaderParser
from pathlib import Path

from usenet_no.archives.encoding import decode_bytes
from usenet_no.mbox_utils import open_source_mbox

logger = logging.getLogger(__name__)

# The end of a message's header block, in either line ending.
_BLANK_LINE = re.compile(rb"\r?\n\r?\n")


@dataclass
class HeaderFieldCounts:
    """How many messages were counted, and how many of them carry each header field."""

    message_count: int
    field_counts: dict[str, int]


def read_header_block(message_file: Path, encoding: str) -> str:
    """Read a message file up to its first blank line and decode it with `encoding`."""
    lines = []
    with message_file.open("rb") as stream:
        for line in stream:
            if not line.strip(b"\r\n"):
                break
            lines.append(line)
    return decode_bytes(b"".join(lines), encoding)


def iter_mbox_header_blocks(mbox_file: Path, encoding: str) -> Iterator[str]:
    """Yield each message in an mbox file as its header block, decoded with `encoding`.

    The messages are read without their envelope line, which is not a header.
    """
    mbox = open_source_mbox(mbox_file)
    # .keys() is load-bearing: mailbox.Mailbox sets __iter__ to itervalues, so
    # iterating the mailbox directly yields messages, which get_bytes rejects.
    for key in mbox.keys():
        raw = mbox.get_bytes(key)
        end_of_headers = _BLANK_LINE.search(raw)
        yield decode_bytes(
            raw[: end_of_headers.start()] if end_of_headers else raw, encoding
        )


def field_names(header_block: str) -> list[str]:
    """The field names one header block carries, each name once, as first spelled."""
    first_spelling: dict[str, str] = {}
    for name in HeaderParser().parsestr(header_block).keys():
        first_spelling.setdefault(name.lower(), name)
    return list(first_spelling.values())


def _by_descending_count(counted: tuple[str, int]) -> tuple[int, str]:
    """Sort key ordering counted names by descending count, then by name."""
    name, count = counted
    return -count, name


def count_header_fields(header_blocks: Iterable[str]) -> HeaderFieldCounts:
    """Count how many header blocks carry each field, matching field names case-insensitively.

    Each field is reported under the spelling most of its messages use, ordered
    by descending count and then by name, so reruns produce identical output.
    """
    message_count = 0
    field_counts: Counter[str] = Counter()
    spellings: dict[str, Counter[str]] = defaultdict(Counter)
    for header_block in header_blocks:
        message_count += 1
        for name in field_names(header_block):
            field_counts[name.lower()] += 1
            spellings[name.lower()][name] += 1
    return HeaderFieldCounts(
        message_count=message_count,
        field_counts={
            min(spellings[lowered].items(), key=_by_descending_count)[0]: count
            for lowered, count in sorted(field_counts.items(), key=_by_descending_count)
        },
    )


def write_header_field_counts(counts: HeaderFieldCounts, output_file: Path) -> None:
    """Write one row per header field: the field, the messages carrying it, and their share."""
    output_file.parent.mkdir(parents=True, exist_ok=True)
    with output_file.open("w", encoding="utf-8", newline="") as file:
        writer = csv.writer(file)
        writer.writerow(["field", "message_count", "proportion_of_messages"])
        for field, count in counts.field_counts.items():
            writer.writerow([field, count, round(count / counts.message_count, 6)])
    logger.info(
        "Wrote %d header fields found in %d messages to %s",
        len(counts.field_counts),
        counts.message_count,
        output_file,
    )
