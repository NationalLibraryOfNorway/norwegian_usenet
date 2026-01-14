from email import policy
from email.parser import BytesParser
import mailbox
import re


def message_factory(fp: mailbox._PartialFile) -> mailbox.mboxMessage:
    utf8_message_parser = BytesParser(policy=policy.default.clone(utf8=True))
    return mailbox.mboxMessage(utf8_message_parser.parse(fp))


def extract_email(from_field: str) -> str | None:
    """
    Extracts the email address from the 'From:' field
    """
    match = re.search(r"[\w\.-]+@[\w\.-]+", from_field)
    return match.group(0) if match else None
