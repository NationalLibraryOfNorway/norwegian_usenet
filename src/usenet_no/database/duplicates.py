"""Counting true duplicate messages in the database.

A *true duplicate* is the same message stored more than once in the same mbox
file: same Message-ID and identical body. These are redundant copies. Since
the database stores every copy as its own row and `newsgroup` names the mbox
file a copy came from, true duplicates are rows sharing (archive, newsgroup,
message_id_hash, body_hash). Message ids that carry *different* bodies are a
separate question, in `usenet_no.database.conflicts`.
"""

import logging
import sqlite3
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class DuplicateMessage:
    """A message stored more than once in the same mbox file."""

    archive: str
    newsgroup: str
    message_id_hash: str
    count: int  # how many copies are present, counting the first


def find_true_duplicates(connection: sqlite3.Connection) -> list[DuplicateMessage]:
    """Find message ids stored more than once with the same body in one mbox file.

    Messages without a Message-ID are skipped: without an id we cannot tell a
    redundant copy from two genuinely identical postings. Copies are grouped by
    (message_id_hash, body_hash), so two versions of a posting are not mistaken
    for duplicates of each other; where an id does have several bodies, `count`
    covers every copy belonging to a repeated body. Sorted by (archive,
    newsgroup, message_id_hash).
    """
    rows = connection.execute(
        "SELECT archive, newsgroup, message_id_hash, SUM(copies)"
        " FROM ("
        "     SELECT archive, newsgroup, message_id_hash, COUNT(*) AS copies"
        "     FROM messages"
        "     WHERE message_id_hash IS NOT NULL"
        "     GROUP BY archive, newsgroup, message_id_hash, body_hash"
        "     HAVING COUNT(*) > 1"
        " )"
        " GROUP BY archive, newsgroup, message_id_hash"
        " ORDER BY archive, newsgroup, message_id_hash"
    )
    return [
        DuplicateMessage(
            archive=archive,
            newsgroup=newsgroup,
            message_id_hash=message_id_hash,
            count=count,
        )
        for archive, newsgroup, message_id_hash, count in rows
    ]
