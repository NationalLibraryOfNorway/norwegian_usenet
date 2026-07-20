"""Counting true duplicate messages in the mbox files.

A *true duplicate* is the same message stored more than once in the same mbox
file: same Message-ID and byte-identical body. These are redundant copies that
can be dropped when building the database.

This reads the mbox files directly and holds no database logic, so that the
count stays independent of the data it is used to check. Message ids that carry
*different* bodies are a separate question, in `usenet_no.conflicts`.
"""

import logging
import mailbox
from collections import Counter
from dataclasses import dataclass
from pathlib import Path

from usenet_no.hash import make_hash
from usenet_no.mbox_utils import get_message_body, message_factory, parse_message_id

logger = logging.getLogger(__name__)


@dataclass
class DuplicateMessage:
    """A message stored more than once in the same mbox file."""

    source_archive: str
    newsgroup: str
    message_id: str
    count: int  # how many copies are present, counting the first


def find_true_duplicates_in_mbox_file(
    mbox_file_and_archive: tuple[Path, str],
) -> list[DuplicateMessage]:
    """Find message ids stored more than once with the same body in one mbox file.

    Messages without a Message-ID are skipped: without an id we cannot tell a
    redundant copy from two genuinely identical postings.

    Copies are grouped by (message_id, body) so that two versions of a posting
    are not mistaken for duplicates of each other. Where an id does have several
    bodies, `count` covers every copy belonging to a repeated body.

    Returned sorted by message_id so reruns produce identical output.
    """
    mbox_file, source_archive = mbox_file_and_archive
    copies: Counter[tuple[str, str]] = Counter()

    for message in mailbox.mbox(str(mbox_file), factory=message_factory):
        message_id = parse_message_id(message.get("Message-ID"))
        if message_id is None:
            continue
        copies[(message_id, make_hash(get_message_body(message)))] += 1

    duplicates_by_message_id: Counter[str] = Counter()
    for (message_id, _body_hash), count in copies.items():
        if count > 1:
            duplicates_by_message_id[message_id] += count

    return [
        DuplicateMessage(
            source_archive=source_archive,
            newsgroup=mbox_file.stem,
            message_id=message_id,
            count=count,
        )
        for message_id, count in sorted(duplicates_by_message_id.items())
    ]
