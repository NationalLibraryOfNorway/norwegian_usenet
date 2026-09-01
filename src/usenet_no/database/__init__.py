"""The SQLite databases holding the messages of the two Usenet archives.

Each archive has a database of its own: `ia.db` and `nb.db`, built by the same
code from the same schema, so either can be read, shared or rebuilt without the
other. A database holds one row per message in `messages`, one row per (message,
referenced id) pair in `message_references`. The sender is `messages.email_id`,
a row of the archive's user database, which is a file of its own and the only
one holding a hashed address. Message ids and bodies appear only as hashes, so
the archive's own file can be shared. No free text is stored at all: subjects and the Newsgroups header
carried plain text addresses and message ids of their own (cancel messages name
their target id in the subject, mis-addressed posts put an address in the
Newsgroups list), which would have handed back the plain text the hashing is
there to withhold.

Message bodies are not stored either: the content comparison needs exact
equality, not the text itself, so a database holds a hash and the full text
lives only in the mbox files. A row's message is found in them by position:
`id` minus the lowest id of its newsgroup, as `load_id_spans` describes, which
is also how a hash is traced back to its plain text.

Row ids are handed out per database, an email id included, so an id only means
anything together with the archive it was read from. `connect_archives` opens
both archives at once and reads them through views that add that archive back as
a column, which is what lets the two be compared in one query, and lets the
date-filtered IA subset be a WHERE clause instead of a copy on disk.

Because the email ids are unrelated between the two files, matching a user across
the archives means matching the hashed address, which lives only in the user
databases: `connect_archives_and_users` opens those as well. Anything counting
users within one archive needs no such thing, and reads `messages.email_id`.
"""

from usenet_no.database.core import (
    IA_ARCHIVE,
    NB_ARCHIVE,
    connect,
    connect_archive_and_users,
    connect_archives,
    connect_archives_and_users,
)

__all__ = [
    "IA_ARCHIVE",
    "NB_ARCHIVE",
    "connect",
    "connect_archive_and_users",
    "connect_archives",
    "connect_archives_and_users",
]
