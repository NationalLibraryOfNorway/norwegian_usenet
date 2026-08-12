# Step 02: loading both archives into the database

- [01_build_database.py](01_build_database.py) reads the .mbox files of both archives and writes `data/output/02_build_database/usenet.db` in one pass. It holds one row per message, with names, emails and message ids as hashes only, so it can be shared.

## The tables

Every hash column holds a 16 character hex digest, from `blake2b` with an 8 byte
digest, of the UTF-8 plain text. A hash is traced back to its plain text through
the mbox files, by the position `messages.id` gives. The schema is in
[`src/usenet_no/database/build.py`](../../src/usenet_no/database/build.py).

```sql
CREATE TABLE users (
    id         INTEGER PRIMARY KEY,
    name_hash  TEXT,
    email_hash TEXT
);

CREATE TABLE messages (
    id              INTEGER PRIMARY KEY,
    archive         TEXT NOT NULL,
    newsgroup       TEXT NOT NULL,
    message_id_hash TEXT,
    user_id         INTEGER REFERENCES users(id),
    date            TEXT,
    body_hash       TEXT
);

CREATE TABLE message_references (
    message_row_id     INTEGER NOT NULL REFERENCES messages(id),
    referenced_id_hash TEXT NOT NULL
);

CREATE INDEX idx_users_email_hash ON users(email_hash);
CREATE INDEX idx_messages_archive_newsgroup ON messages(archive, newsgroup);
CREATE INDEX idx_messages_message_id_hash ON messages(message_id_hash);
CREATE INDEX idx_messages_user_id ON messages(user_id);
CREATE INDEX idx_messages_date ON messages(date);
CREATE INDEX idx_messages_body_hash ON messages(body_hash);
CREATE INDEX idx_references_row_id ON message_references(message_row_id);
CREATE INDEX idx_references_hash ON message_references(referenced_id_hash);
```

`messages`, one row per message read from an mbox file:

| Column            | Type    | Null | Description                                                                                      |
| ----------------- | ------- | ---- | ------------------------------------------------------------------------------------------------ |
| `id`              | INTEGER | no   | Row id. Minus the lowest id of its (archive, newsgroup), it is the message's position in its mbox file |
| `archive`         | TEXT    | no   | `ia` or `nb`                                                                                     |
| `newsgroup`       | TEXT    | no   | Stem of the mbox file the message was read from                                                  |
| `message_id_hash` | TEXT    | yes  | Hash of the Message-ID header; NULL when the header is missing or unparseable                    |
| `user_id`         | INTEGER | yes  | `users.id` of the sender; NULL when the From field gave neither a name nor an email              |
| `date`            | TEXT    | yes  | `YYYY-MM-DD`; NULL when the Date header could not be parsed                                      |
| `body_hash`       | TEXT    | yes  | Hash of the message body; NULL when the body is empty. The body itself is not stored |

28 messages have a NULL `message_id_hash`, all of them from IA. Every one of them
does carry a Message-ID line in the mbox file, but a mangled From or Subject
header earlier in the message contains a raw newline, which ends the header block
where the parser is concerned: the Message-ID, and every header after it, is read
as part of the body instead. The same goes for their Date, which is NULL for 27 of
the 28.

`users`, one row per (name, email) pair:

| Column       | Type    | Null | Description                                        |
| ------------ | ------- | ---- | -------------------------------------------------- |
| `id`         | INTEGER | no   | Row id, referenced by `messages.user_id`            |
| `name_hash`  | TEXT    | yes  | Hash of the display name; NULL when there is none   |
| `email_hash` | TEXT    | yes  | Hash of the lowercased address; NULL when there is none |

`message_references`, one row per (message, referenced id) pair from the References header:

| Column               | Type    | Null | Description                                                                     |
| -------------------- | ------- | ---- | ------------------------------------------------------------------------------- |
| `message_row_id`     | INTEGER | no   | `messages.id` of the referring message                                          |
| `referenced_id_hash` | TEXT    | no   | Hash of the referenced message id. Joins to `messages.message_id_hash` when that message is in the archives |

### Row counts

Built from both archives in full:

| Table                | Rows       |
| -------------------- | ---------- |
| `messages`           | 6 594 990  |
| `users`              | 250 829    |
| `message_references` | 27 382 713 |

## Checking a database built somewhere else

A message's position in its mbox file is its row id minus the lowest row id of its
(archive, newsgroup), so the ids are not just labels: the replacement-character pairs
and the embeddings both use them to find bodies. Two databases holding the same messages
under different ids will read the wrong bodies without reporting anything wrong, because
the message counts still agree.

The scripts below print a fingerprint of the rows themselves rather than of the .db file,
which is not byte-reproducible between builds. Run one on each machine and compare the
output. They read the database read-only, and use nothing outside the standard library,
so they can be copied to a machine that has neither this repository nor its dependencies.

- [02_fingerprint_database.py](02_fingerprint_database.py) hashes every table, row ids included. Start here: if every line matches, the two databases are interchangeable.
- [03_fingerprint_database_content.py](03_fingerprint_database_content.py) says whether a difference is in the data or only in the ids it was given, by hashing the message and user rows with the ids left out, next to the order the mbox files were read in.
- [04_fingerprint_database_per_archive.py](04_fingerprint_database_per_archive.py) splits the fingerprint by archive. Every IA file is read before any NB file, so a sender first seen in IA is numbered while IA is being read: this says which parse a difference came from.
