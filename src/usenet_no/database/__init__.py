"""The SQLite database holding the messages of both Usenet archives.

It holds one row per message in `messages`, one row per (message, referenced id)
pair in `message_references` and one row per sender in `users`. Names, emails,
message ids and bodies appear only as hashes, so the file can be shared. No free
text is stored at all: subjects and the Newsgroups header carried plain text
addresses and message ids of their own (cancel messages name their target id in
the subject, mis-addressed posts put an address in the Newsgroups list), which
would have handed back the plain text the hashing is there to withhold.

Message bodies are not stored either: the content comparison needs exact
equality, not the text itself, so the database holds a hash and the full text
lives only in the mbox files. A row's message is found in them by position:
`id` minus the lowest id of its (archive, newsgroup), as `load_id_spans`
describes, which is also how a hash is traced back to its plain text.

The `archive` column distinguishes the two sources, so analyses that used to
run once per archive directory become a GROUP BY, and the date-filtered IA
subset becomes a WHERE clause instead of a copy on disk.
"""

from usenet_no.database.core import IA_ARCHIVE, NB_ARCHIVE, connect

__all__ = [
    "IA_ARCHIVE",
    "NB_ARCHIVE",
    "connect",
]
