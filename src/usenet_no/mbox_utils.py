from email import policy
from email.parser import BytesParser
from tqdm import tqdm

import mailbox
import logging
import re
from pathlib import Path
from typing import Iterator

logger = logging.getLogger(__name__)


def message_factory(fp: mailbox._PartialFile) -> mailbox.mboxMessage:
    utf8_message_parser = BytesParser(policy=policy.default.clone(utf8=True))
    return mailbox.mboxMessage(utf8_message_parser.parse(fp))


def ensure_mbox_envelope(text: str) -> str:
    if not text.startswith("From "):
        match = re.search(r"^From:[ \t]*(.*)", text, re.MULTILINE)
        sender = match.group(1).strip() if match else ""
        return f"From {sender}\n" + text
    return text


def get_from_field(message: mailbox.mboxMessage) -> str:
    return message["From"] or message.get_from()


def get_messages_from_field(mbox_file: Path) -> Iterator[str]:
    """Iterates over every message in mbox file and yields the value in the From field of every message"""
    mbox = mailbox.mbox(str(mbox_file), factory=message_factory)
    for message in tqdm(
        mbox, desc=f"Getting From field from each message in {mbox_file}"
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


def get_messages_date_field(mbox_file: Path) -> Iterator[str | None]:
    mbox = mailbox.mbox(str(mbox_file), factory=message_factory)
    for message in tqdm(mbox, desc=f"Getting dates from each message in {mbox_file}"):
        date_field = message.get("Date", None)
        yield date_field
