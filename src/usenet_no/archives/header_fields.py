"""The message header fields the archives carry.

The NB sources hold one message per file and the IA sources one mbox file per
newsgroup, so each has its own way of reading header blocks out of them; the
counting and the file written are shared.
"""

import csv
import logging
import re
from collections import Counter, defaultdict
from collections.abc import Iterable, Iterator
from dataclasses import dataclass
from pathlib import Path

from usenet_no.archives.encoding import decode_bytes

logger = logging.getLogger(__name__)

# Every line ending the sources hold, including the lone carriage returns some
# messages carry inside a header value.
LINE_END = re.compile(r"\r\n|\r|\n")

# A header line: a field name of printable ASCII but the colon, then the colon.
FIELD_LINE = re.compile(r"([\041-\071\073-\176]+):")


@dataclass
class HeaderFieldCounts:
    """How many messages were counted, and how many of them carry each header field."""

    message_count: int
    field_counts: dict[str, int]


@dataclass
class MboxMessageHeaders:
    """One message of an mbox file: the line it starts on, and its header block."""

    line_number: int
    header_block: str


def read_header_block(message_file: Path, encoding: str) -> str:
    """Read a message file up to its first blank line and decode it with `encoding`."""
    lines = []
    with message_file.open("rb") as stream:
        for line in stream:
            if not line.strip(b"\r\n"):
                break
            lines.append(line)
    return decode_bytes(b"".join(lines), encoding)


def _is_envelope_line(line: bytes, envelope_pattern: re.Pattern[bytes]) -> bool:
    """Whether the line is an envelope line of the form the file delimits messages with."""
    return bool(
        line.startswith(b"From ") and envelope_pattern.match(line.rstrip(b"\r\n"))
    )


def _message_headers(
    line_number: int, header_lines: list[bytes], encoding: str
) -> MboxMessageHeaders:
    """One message's read header lines, decoded with `encoding`."""
    return MboxMessageHeaders(
        line_number=line_number,
        header_block=decode_bytes(b"".join(header_lines), encoding),
    )


def iter_mbox_message_headers(
    mbox_file: Path, encoding: str, envelope_pattern: re.Pattern[bytes]
) -> Iterator[MboxMessageHeaders]:
    """Yield the header block of each message in an mbox file, and the 1-based line it starts on.

    A message starts at a line matching `envelope_pattern`, which is not a header
    itself, and its headers run to the first blank line. Lines ahead of the first
    envelope line belong to no message.
    """
    start_line = 0
    header_lines: list[bytes] = []
    in_headers = False
    with mbox_file.open("rb") as stream:
        for line_number, line in enumerate(stream, start=1):
            if _is_envelope_line(line, envelope_pattern):
                if start_line:
                    yield _message_headers(start_line, header_lines, encoding)
                start_line = line_number
                header_lines = []
                in_headers = True
            elif not in_headers:
                continue
            elif line.strip(b"\r\n"):
                header_lines.append(line)
            else:
                in_headers = False
    if start_line:
        yield _message_headers(start_line, header_lines, encoding)


def _first_spellings(names: Iterable[str]) -> list[str]:
    """Each name once, as first spelled, matched case-insensitively."""
    first_spelling: dict[str, str] = {}
    for name in names:
        first_spelling.setdefault(name.lower(), name)
    return list(first_spelling.values())


def field_names(header_block: str) -> list[str]:
    """The field names one header block carries, each name once, as first spelled.

    Lines are split on carriage return, newline, and the two together, as the
    sources hold all three. A line that is not a field, be it a folded value or
    one the source mangled, is passed over, and the fields below it still count.
    """
    return _first_spellings(
        field.group(1)
        for line in LINE_END.split(header_block)
        if (field := FIELD_LINE.match(line))
    )


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
