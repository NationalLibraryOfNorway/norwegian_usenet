"""The SQLite databases holding the messages of the two Usenet archives.

Each archive has a database of its own: `ia.db` and `nb.db`, built by the same
code from the same schema, so either can be read, shared or rebuilt without the
other. A database holds one row per message in `messages`, one row per (message,
referenced id) pair in `message_references`. A user is an email address, and
`messages.email_id` names one in the archive's user database, a file of its own
that is not published with this one. Message ids and bodies appear only as
hashes, so the archive's own file can be shared. No free text is stored at all:
subjects and the Newsgroups header
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
`connect_archive` opens one of them through the same views, for the counts that
read a single archive, and `connect_archives_and_users` attaches the user
databases too, for the comparisons that match a user across the archives.
"""

from usenet_no.database.core import (
    IA_ARCHIVE,
    NB_ARCHIVE,
    connect,
    connect_archive,
    connect_archive_and_users,
    connect_archives,
    connect_archives_and_users,
)

__all__ = [
    "IA_ARCHIVE",
    "NB_ARCHIVE",
    "connect",
    "connect_archive",
    "connect_archive_and_users",
    "connect_archives",
    "connect_archives_and_users",
]
