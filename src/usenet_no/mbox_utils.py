import mailbox
import re
from collections.abc import Collection, Iterable
from email import policy
from email.parser import BytesParser
from pathlib import Path

_MESSAGE_ID_PATTERN = re.compile(r"<[^>]+>")


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


def write_mbox(messages: Iterable[str], outfile: Path, append: bool = False) -> None:
    """Write messages to outfile with consistent normalization.

    Each message gets ensure_mbox_envelope applied, trailing whitespace stripped,
    and is separated by a blank line. Written as UTF-8 bytes.
    Use append=True when multiple sources contribute to the same output file.
    """
    mode = "ab" if append else "wb"
    with outfile.open(mode) as f:
        for text in messages:
            normalized = ensure_mbox_envelope(text).rstrip() + "\n\n"
            f.write(normalized.encode("utf-8"))


def ensure_mbox_envelope(text: str) -> str:
    """Prefix an mbox "From " delimiter line if the text lacks one."""
    if not text.startswith("From "):
        # Placeholder sender for the mbox "From " delimiter line
        return "From MAILER-DAEMON\n" + text
    return text


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
    """Return the message body as whitespace-normalized text."""
    if message.is_multipart():
        parts = [
            _decode_mbox_message(part)
            for part in message.walk()
            if part.get_content_type() == "text/plain"
        ]
        return _normalize_whitespace(" ".join(parts))
    return _normalize_whitespace(_decode_mbox_message(message))


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
