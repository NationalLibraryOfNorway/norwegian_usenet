from email import policy
from email.parser import BytesParser
from tqdm import tqdm

import mailbox
import logging
import re
from pathlib import Path
from typing import Iterable, Iterator

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
    if not text.startswith("From "):
        match = re.search(r"^From:[ \t]*(.*)", text, re.MULTILINE)
        sender = match.group(1).strip() if match else ""
        return f"From {sender}\n" + text
    return text


def get_from_field(message: mailbox.mboxMessage) -> str:
    return message["From"] or message.get_from()


def get_messages_from_field(
    mbox_file: Path, show_progress: bool = True
) -> Iterator[str]:
    """Iterates over every message in mbox file and yields the value in the From field of every message"""
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


def get_message_body(message: mailbox.mboxMessage) -> str:
    if message.is_multipart():
        parts = []
        for part in message.walk():
            if part.get_content_type() == "text/plain":
                payload = part.get_payload(decode=True)
                if payload:
                    parts.append(payload.decode("utf-8", errors="replace").strip())
        body = "\n".join(parts)
    else:
        payload = message.get_payload(decode=True)
        body = payload.decode("utf-8", errors="replace") if payload else ""
    return body


def get_message_bodies(mbox_file: Path) -> set[str]:
    """Returns the set of unique message bodies in an mbox file, excluding headers.

    Assumes all message payloads are UTF-8 encoded on disk, regardless of the
    charset declared in Content-Type headers. This holds for both data sources:
    - NWA (data/nwa_90s/utf_8_data): src/usenet_no/parse_norwegian_web_archive.py decodes each file with
      chardet and writes as UTF-8 via write_mbox.
    - IA (data/internet_archive/utf_8_data): src/usenet_no/parse_internet_archive.py detects encoding with
      chardet and writes each message as UTF-8 via write_mbox.
    """
    mbox = mailbox.mbox(str(mbox_file), factory=message_factory)
    bodies = set()
    for message in mbox:
        body = get_message_body(message=message)
        if body:
            bodies.add(body)
    return bodies


def get_messages_date_field(mbox_file: Path) -> Iterator[str | None]:
    mbox = mailbox.mbox(str(mbox_file), factory=message_factory)
    for message in mbox:
        date_field = message.get("Date", None)
        yield date_field
