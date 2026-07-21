"""Everything that creates or queries the SQLite databases.

`core` builds the shared and private databases from the mbox files;
`statistics`, `comparison` and `conflicts` query the shared one. The core API
is re-exported here, so callers import it as `usenet_no.database`.
"""

from usenet_no.database.core import (
    IA_ARCHIVE,
    NB_ARCHIVE,
    UNKNOWN_DATE,
    ExtractedMessage,
    UserKey,
    connect,
    create_private_schema,
    create_schema,
    date_span_clause,
    extract_message,
    extract_messages_from_mbox_file,
    insert_messages,
    load_user_ids,
)

__all__ = [
    "IA_ARCHIVE",
    "NB_ARCHIVE",
    "UNKNOWN_DATE",
    "ExtractedMessage",
    "UserKey",
    "connect",
    "create_private_schema",
    "create_schema",
    "date_span_clause",
    "extract_message",
    "extract_messages_from_mbox_file",
    "insert_messages",
    "load_user_ids",
]
