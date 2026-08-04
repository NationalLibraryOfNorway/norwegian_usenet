import mailbox
import re
from collections.abc import Collection, Iterable
from dataclasses import dataclass
from email import policy
from email.parser import BytesParser
from pathlib import Path

_MESSAGE_ID_PATTERN = re.compile(r"<[^>]+>")

# mailbox.mbox starts a new message at every line beginning with "From ", so a
# body line that does too is escaped with a leading ">" on the way out, and any
# ">" already in front of one is doubled so the escaping can be undone.
_FROM_LINE = re.compile(r"^(>*From )", re.MULTILINE)
_ESCAPED_FROM_LINE = re.compile(r"^>(>*From )", re.MULTILINE)

# Written as the envelope line for a message whose source has none of its own.
PLACEHOLDER_ENVELOPE = "From MAILER-DAEMON"

# Every message the IA archive holds is delimited by an envelope line carrying a
# Google Groups id, and every one of them also carries an X-Google or Google Xref
# header. The 3497 "From " lines in the archive that take neither form take
# neither, so they are body text rather than the start of a message.
IA_SOURCE_ENVELOPE = re.compile(rb"From -?\d+$")

# What write_mbox writes: the source's own envelope line where it had one, and
# PLACEHOLDER_ENVELOPE where it did not.
WRITTEN_ENVELOPE = re.compile(rb"From (-?\d+|MAILER-DAEMON)$")


@dataclass
class RawMessage:
    """One message of an mbox file: its envelope line, and its headers and body.

    `text` holds the message as it reads, with no "From " escaping applied.
    `envelope` is None for a source that carries no envelope line of its own.
    """

    envelope: str | None
    text: str


def _normalize_whitespace(text: str) -> str:
    """Collapse every run of whitespace to a single space and strip the ends.

    Folds away the differences that come from the two archives reflowing or
    re-wrapping the same text: trailing spaces, CRLF vs LF, blank-line runs.
    """
    return " ".join(text.split())


def parse_message_id(raw: str | None) -> str | None:
    """Extract the bare message-id (with angle brackets) from a Message-ID header value.

    Strips trailing junk like '#1/1' that some IA messages append.
    Returns None if no valid id is found.
    """
    if not raw:
        return None
    m = _MESSAGE_ID_PATTERN.search(raw)
    return m.group(0).lower() if m else None


def parse_references(raw: str | None) -> list[str]:
    """Extract all message-ids from a References header value."""
    if not raw:
        return []
    return [mid.lower() for mid in _MESSAGE_ID_PATTERN.findall(raw)]


def message_factory(fp: mailbox._PartialFile) -> mailbox.mboxMessage:
    utf8_message_parser = BytesParser(policy=policy.default.clone(utf8=True))
    return mailbox.mboxMessage(utf8_message_parser.parse(fp))


class StrictMbox(mailbox.mbox):
    """An mbox whose messages begin only at an envelope line matching a pattern.

    mailbox.mbox begins a message at every line starting with "From ", which body
    lines do too. `rejected_envelope_count` and `bytes_before_first_message` hold
    what this reader passed over: the "From " lines it read as body text, and any
    bytes ahead of the first envelope line, which have no message to belong to.
    """

    def __init__(self, path: Path, envelope_pattern: re.Pattern[bytes]) -> None:
        self._envelope_pattern = envelope_pattern
        self.rejected_envelope_count = 0
        self.bytes_before_first_message = 0
        super().__init__(str(path), factory=message_factory)

    def _is_envelope(self, line: bytes) -> bool:
        """Whether the line delimits a message. The prefix test keeps the regex off every line."""
        return bool(
            line.startswith(b"From ")
            and self._envelope_pattern.match(line.rstrip(b"\r\n"))
        )

    def _generate_toc(self) -> None:
        """As mailbox.mbox._generate_toc, except for which lines start a message."""
        starts, stops = [], []
        self.rejected_envelope_count = 0
        last_was_empty = False
        self._file.seek(0)
        while True:
            line_pos = self._file.tell()
            line = self._file.readline()
            if self._is_envelope(line):
                if len(stops) < len(starts):
                    if last_was_empty:
                        stops.append(line_pos - len(mailbox.linesep))
                    else:
                        stops.append(line_pos)
                starts.append(line_pos)
                last_was_empty = False
            elif not line:
                if last_was_empty:
                    stops.append(line_pos - len(mailbox.linesep))
                else:
                    stops.append(line_pos)
                break
            else:
                if line.startswith(b"From "):
                    self.rejected_envelope_count += 1
                last_was_empty = line == mailbox.linesep
        self.bytes_before_first_message = starts[0] if starts else 0
        self._toc = dict(enumerate(zip(starts, stops)))
        self._next_key = len(self._toc)
        self._file_length = self._file.tell()


def open_source_mbox(mbox_file: Path) -> StrictMbox:
    """Open an mbox file as the IA archive holds it, where every envelope carries a Google Groups id."""
    return StrictMbox(mbox_file, IA_SOURCE_ENVELOPE)


def open_mbox(mbox_file: Path) -> StrictMbox:
    """Open an mbox file that write_mbox wrote."""
    return StrictMbox(mbox_file, WRITTEN_ENVELOPE)


def escape_from_lines(text: str) -> str:
    """Prefix ">" to every line starting with "From ", or with ">" runs before it."""
    return _FROM_LINE.sub(r">\1", text)


def unescape_from_lines(text: str) -> str:
    """Undo `escape_from_lines`, removing one ">" from each escaped line."""
    return _ESCAPED_FROM_LINE.sub(r"\1", text)


def split_envelope(text: str) -> tuple[str | None, str]:
    """Split a leading mbox "From " line off the rest of the message text.

    Call this for text read out of an mbox file, where the first line is the
    envelope. Returns (None, text) when there is no such line.
    """
    if not text.startswith("From "):
        return None, text
    envelope, _, rest = text.partition("\n")
    return envelope, rest


def write_mbox(
    messages: Iterable[RawMessage], outfile: Path, append: bool = False
) -> None:
    """Write each message to outfile as UTF-8 bytes, separated by a blank line.

    Every message gets an envelope line, and "From " lines in its text are
    escaped, so the envelope lines are the only message delimiters in the file.
    Use append=True when multiple sources contribute to the same output file.
    """
    mode = "ab" if append else "wb"
    with outfile.open(mode) as f:
        for message in messages:
            text = escape_from_lines(message.text)
            if text and not text.endswith("\n"):
                text += "\n"
            envelope = message.envelope or PLACEHOLDER_ENVELOPE
            f.write(f"{envelope}\n{text}\n".encode("utf-8"))


def get_from_field(message: mailbox.mboxMessage) -> str | None:
    """Return the From header, or None when the message has none."""
    return message["From"]


def _decode_bytes(payload: bytes, charset: str | None) -> str:
    """Decode body bytes, preferring UTF-8 and falling back to the declared charset.

    Both archives are largely UTF-8 on disk. Bytes that are not valid UTF-8 fall
    back to the declared charset, then to Latin-1.
    """
    try:
        return payload.decode("utf-8")
    except UnicodeDecodeError:
        pass
    if charset:
        try:
            return payload.decode(charset, errors="replace")
        except LookupError:
            pass
    return payload.decode("latin-1", errors="replace")


def _decode_mbox_message(part: mailbox.mboxMessage) -> str:
    """Decode one message or part's body bytes to text.

    A declared quoted-printable or base64 body is reversed by get_payload, then
    the bytes are decoded by `_decode_bytes`.
    """
    payload = part.get_payload(decode=True)
    if not payload:
        return ""

    return _decode_bytes(payload, part.get_content_charset())


def get_message_body(message: mailbox.mboxMessage) -> str:
    """Return the message body as whitespace-normalized text, with "From " lines unescaped.

    Unescaping runs before normalizing, since it anchors on line starts.
    """
    if message.is_multipart():
        parts = [
            _decode_mbox_message(part)
            for part in message.walk()
            if part.get_content_type() == "text/plain"
        ]
        return _normalize_whitespace(unescape_from_lines(" ".join(parts)))
    return _normalize_whitespace(unescape_from_lines(_decode_mbox_message(message)))


def get_message_bodies_at_positions(
    mbox_file: Path,
    positions: Collection[int],
    expected_message_count: int | None = None,
) -> dict[int, str]:
    """Return the body of the message at each 0-based position in the file's message order.

    mailbox.mbox assigns keys 0..n-1 in file order, so each wanted message is
    read directly instead of parsing the whole file. `expected_message_count`
    checks the file's message count, so a caller that computed the positions
    elsewhere (e.g. from database row ids) notices when the file does not match.
    """
    mbox = mailbox.mbox(str(mbox_file), factory=message_factory)
    message_count = len(mbox)
    if expected_message_count is not None and message_count != expected_message_count:
        raise ValueError(
            f"{mbox_file} holds {message_count} messages, expected {expected_message_count}"
        )

    out_of_range = [position for position in positions if position >= message_count]
    if out_of_range:
        raise ValueError(
            f"{mbox_file} holds {message_count} messages,"
            f" so it has no message at positions {sorted(out_of_range)}"
        )

    return {
        position: get_message_body(mbox[position]) for position in sorted(positions)
    }
