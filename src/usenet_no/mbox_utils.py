from email import policy
from email.parser import BytesParser
import mailbox
import logging
from pathlib import Path
from typing import Iterator

logger = logging.getLogger(__name__)


def message_factory(fp: mailbox._PartialFile) -> mailbox.mboxMessage:
    utf8_message_parser = BytesParser(policy=policy.default.clone(utf8=True))
    return mailbox.mboxMessage(utf8_message_parser.parse(fp))


def get_messages_from_field(mbox_file: Path) -> Iterator[str]:
    """Iterates over every message in mbox file and yields the value in the From field of every message"""
    mbox = mailbox.mbox(str(mbox_file), factory=message_factory)
    for message in mbox:
        try:
            message_from = message["From"] or message.get_from()
            yield message_from
        except Exception as e:
            logger.warning(e)
            logger.debug("dir(message): %s", dir(message))
            logger.debug("message: %s", message)
            yield ""
