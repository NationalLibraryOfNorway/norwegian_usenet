import logging
import mailbox
import re
from collections.abc import Collection, Iterable, Iterator
from email import policy
from email.parser import BytesParser
from pathlib import Path

from tqdm import tqdm

_MESSAGE_ID_PATTERN = re.compile(r"<[^>]+>")

logger = logging.getLogger(__name__)


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


def write_mbox(messages: Iterable[str], outfile: Path, append: bool = False) -> int:
    """Write messages to outfile with consistent normalization.

    Each message gets ensure_mbox_envelope applied, trailing whitespace stripped,
    and is separated by a blank line. Written as UTF-8 bytes.
    Use append=True when multiple sources contribute to the same output file.
    Returns the number of messages written.
    """
    count = 0
    mode = "ab" if append else "wb"
    with outfile.open(mode) as f:
        for text in messages:
            normalized = ensure_mbox_envelope(text).rstrip() + "\n\n"
            f.write(normalized.encode("utf-8"))
            count += 1
    return count


def ensure_mbox_envelope(text: str) -> str:
    """Prefix an mbox "From " delimiter line if the text lacks one."""
    if not text.startswith("From "):
        # Placeholder sender for the mbox "From " delimiter line
        return "From MAILER-DAEMON\n" + text
    return text


def get_from_field(message: mailbox.mboxMessage) -> str | None:
    """Return the From header, or None when the message has none."""
    return message["From"]


def get_messages_from_field(
    mbox_file: Path, show_progress: bool = True
) -> Iterator[str | None]:
    """Iterates over every message in mbox file and yields the value in the From field of every message.

    Yields None for messages that carry no From header, i.e. whose sender is unknown.
    """
    mbox = mailbox.mbox(str(mbox_file), factory=message_factory)
    for message in tqdm(
        mbox,
        desc=f"Getting From field from each message in {mbox_file}",
        disable=not show_progress,
    ):
        try:
            message_from = get_from_field(message)
            yield message_from
        except IndexError:
            logger.debug(
                "IndexError when accessing message From field (From field is probably '=?ISO-8859-15?Q??=')"
            )
            logger.debug("message: %s", message)
            yield ""

        except Exception as e:
            logger.warning(
                "Other exception when accessing message from field: %s %s", type(e), e
            )
            logger.debug("message: %s", message)
            yield ""


def _decode_bytes(payload: bytes, charset: str | None) -> str:
    """Decode body bytes, preferring UTF-8 and falling back to the declared charset.

    Both archives are largely UTF-8 on disk, so valid UTF-8 is read as UTF-8.
    Only bytes that are not valid UTF-8 (the raw 8-bit / Latin-1 bodies IA)
    fall back to the declared charset, then Latin-1.
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
    the bytes are decoded by `_decode_bytes`. Undeclared quoted-printable (=XX
    escapes with no Content-Transfer-Encoding header) is deliberately left as-is
    rather than guessed at, to avoid mis-decoding text that only looks like it;
    usenet_no.quoted_printable is used to count those messages, not convert them.
    """
    payload = part.get_payload(decode=True)
    if not payload:
        return ""

    return _decode_bytes(payload, part.get_content_charset())


def get_message_body(message: mailbox.mboxMessage) -> str:
    if message.is_multipart():
        parts = []
        for part in message.walk():
            if part.get_content_type() == "text/plain":
                decoded = _decode_mbox_message(part)
                if decoded:
                    parts.append(decoded.strip())
        return "\n".join(parts)
    return _decode_mbox_message(message)


def get_message_bodies(mbox_file: Path) -> set[str]:
    """Returns the set of unique message bodies in an mbox file, excluding headers.

    Assumes all message payloads are UTF-8 encoded on disk, regardless of the
    charset declared in Content-Type headers. This holds for both data sources:
    - NB (data/input/nb/utf_8_data): archives/parse_norwegian_web_archive.py
      decodes each file with chardet and writes as UTF-8 via write_mbox.
    - IA (data/input/internet_archive/utf_8_data):
      archives/parse_internet_archive.py detects encoding with chardet and
      writes each message as UTF-8 via write_mbox.
    """
    mbox = mailbox.mbox(str(mbox_file), factory=message_factory)
    bodies = set()
    for message in mbox:
        body = get_message_body(message=message)
        if body:
            bodies.add(body)
    return bodies


def get_message_bodies_at_positions(
    mbox_file: Path,
    positions: Collection[int],
    expected_message_count: int | None = None,
) -> dict[int, str]:
    """Return the body of the message at each 0-based position in the file's message order.

    mailbox.mbox assigns keys 0..n-1 in file order, so each wanted message is
    read directly instead of parsing the whole file. When
    `expected_message_count` is given, the file's message count is checked
    against it, so a caller that computed the positions elsewhere (e.g. from
    database row ids) notices when the file does not match.
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


def get_messages_date_field(mbox_file: Path) -> Iterator[str | None]:
    mbox = mailbox.mbox(str(mbox_file), factory=message_factory)
    for message in mbox:
        date_field = message.get("Date", None)
        yield date_field
