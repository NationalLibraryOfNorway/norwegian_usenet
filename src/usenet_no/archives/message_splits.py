"""Whether the IA sources are split into messages only where a message starts.

`mailbox` starts a message at every line beginning with "From ", and the IA
sources leave the ones their message bodies hold unescaped, so the split accepts
only a line carrying a Google Groups id. This reports the "From " lines that
rule passed over, and whether a message's header block follows one after all.
"""

import csv
import logging
import re
from collections.abc import Iterable, Iterator
from dataclasses import dataclass, field
from pathlib import Path

logger = logging.getLogger(__name__)

# Every archived article carries one, so a "From " line with no such header
# under it begins no message.
GOOGLE_HEADER = re.compile(rb"X-Google-Language:", re.IGNORECASE)

# How many lines under a "From " line to keep. A header block is shorter than
# this, and a body paragraph no blank line ends is not one however long it runs.
FOLLOWING_LINE_LIMIT = 100


@dataclass
class RejectedEnvelope:
    """A line beginning with "From " that the envelope pattern did not accept."""

    source_file: str
    line_number: int
    following_lines: list[bytes] = field(default_factory=list)

    @property
    def starts_a_message(self) -> bool:
        """Whether the lines under it are a message header block."""
        return any(GOOGLE_HEADER.match(line) for line in self.following_lines)


def _is_rejected_envelope(line: bytes, envelope_pattern: re.Pattern[bytes]) -> bool:
    """Whether the line begins a message to `mailbox` but not to the pattern."""
    return bool(line.startswith(b"From ") and not envelope_pattern.match(line))


def rejected_envelopes(
    mbox_file: Path, envelope_pattern: re.Pattern[bytes]
) -> Iterator[RejectedEnvelope]:
    """Yield every "From " line of one mbox file the pattern rejected, with the lines under it.

    The lines kept are the ones up to the first blank line, which is as far as a
    header block reaches.
    """
    rejected = None
    with mbox_file.open("rb") as stream:
        for line_number, line in enumerate(stream, start=1):
            text = line.rstrip(b"\r\n")
            if _is_rejected_envelope(text, envelope_pattern):
                if rejected:
                    yield rejected
                rejected = RejectedEnvelope(mbox_file.name, line_number)
            elif rejected is None:
                continue
            elif not text:
                yield rejected
                rejected = None
            elif len(rejected.following_lines) < FOLLOWING_LINE_LIMIT:
                rejected.following_lines.append(text)
    if rejected:
        yield rejected


def write_rejected_envelopes(
    rejected: Iterable[RejectedEnvelope], output_file: Path
) -> None:
    """Write one row per rejected "From " line: its source file, line and whether it starts a message.

    The line itself is left out, message bodies being what this reads.
    """
    output_file.parent.mkdir(parents=True, exist_ok=True)
    counted = starting_a_message = 0
    with output_file.open("w", encoding="utf-8", newline="") as file:
        writer = csv.writer(file)
        writer.writerow(["source_file", "line_number", "starts_a_message"])
        for envelope in rejected:
            counted += 1
            starting_a_message += envelope.starts_a_message
            writer.writerow(
                [envelope.source_file, envelope.line_number, envelope.starts_a_message]
            )
    logger.info(
        "Wrote %d unescaped 'From ' lines, %d of them starting a message, to %s",
        counted,
        starting_a_message,
        output_file,
    )
