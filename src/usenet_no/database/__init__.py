"""The SQLite databases holding the messages of the two Usenet archives.

Each archive has a database of its own: `ia.db` and `nb.db`, built by the same
code from the same schema, so either can be read, shared or rebuilt without the
other. A database holds one row per message in `messages`, one row per (message,
referenced id) pair in `message_references` and one row per sender in `users`.
Names, emails, message ids and bodies appear only as hashes, so the files can be
shared. No free text is stored at all: subjects and the Newsgroups header
carried plain text addresses and message ids of their own (cancel messages name
their target id in the subject, mis-addressed posts put an address in the
Newsgroups list), which would have handed back the plain text the hashing is
there to withhold.

Message bodies are not stored either: the content comparison needs exact
equality, not the text itself, so a database holds a hash and the full text
lives only in the mbox files. A row's message is found in them by position:
`id` minus the lowest id of its newsgroup, as `load_id_spans` describes, which
is also how a hash is traced back to its plain text.

Row ids are handed out per database, so an id, a user id included, only means
anything together with the archive it was read from. `connect_archives` opens
both files at once and reads them through views that add that archive back as a
column, which is what lets the two be compared in one query, and lets the
date-filtered IA subset be a WHERE clause instead of a copy on disk.
"""

from usenet_no.database.core import (
    IA_ARCHIVE,
    NB_ARCHIVE,
    connect,
    connect_archives,
)

__all__ = [
    "IA_ARCHIVE",
    "NB_ARCHIVE",
    "connect",
    "connect_archives",
]
