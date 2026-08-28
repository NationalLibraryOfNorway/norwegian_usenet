# Step 02: loading each archive into a database of its own

- [01_build_databases.py](01_build_databases.py) reads the .mbox files of one archive at a time and writes `data/output/02_build_database/ia.db` and `data/output/02_build_database/nb.db`. Each holds one row per message of that archive, with names, emails and message ids as hashes only, so they can be shared. Run with `--overwrite` to delete existing database files and build them again; without the flag an archive whose file is already there is skipped.

## The tables

Both databases have the same schema, and the archive a row belongs to is the
file it is in. Every hash column holds a 16 character hex digest, from `blake2b`
with an 8 byte digest, of the UTF-8 plain text. A hash is traced back to its
plain text through the mbox files, by the position `messages.id` gives. The
schema is in [`src/usenet_no/database/build.py`](../../src/usenet_no/database/build.py).

```sql
CREATE TABLE users (
    id         INTEGER PRIMARY KEY,
    name_hash  TEXT,
    email_hash TEXT
);

CREATE TABLE messages (
    id              INTEGER PRIMARY KEY,
    newsgroup       TEXT NOT NULL,
    message_id_hash TEXT NOT NULL,
    user_id         INTEGER REFERENCES users(id),
    date            TEXT,
    body_hash       TEXT
);

CREATE TABLE message_references (
    message_row_id     INTEGER NOT NULL REFERENCES messages(id),
    referenced_id_hash TEXT NOT NULL
);

CREATE INDEX idx_users_email_hash ON users(email_hash);
CREATE INDEX idx_messages_newsgroup ON messages(newsgroup);
CREATE INDEX idx_messages_message_id_hash ON messages(message_id_hash);
CREATE INDEX idx_messages_user_id ON messages(user_id);
CREATE INDEX idx_messages_date ON messages(date);
CREATE INDEX idx_messages_body_hash ON messages(body_hash);
CREATE INDEX idx_references_row_id ON message_references(message_row_id);
CREATE INDEX idx_references_hash ON message_references(referenced_id_hash);
```

`messages`, one row per message read from an mbox file:

| Column            | Type    | Null | Description                                                                          |
| ----------------- | ------- | ---- | ------------------------------------------------------------------------------------ |
| `id`              | INTEGER | no   | Row id. Minus the lowest id of its newsgroup, it is the message's position in its mbox file |
| `newsgroup`       | TEXT    | no   | Stem of the mbox file the message was read from                                      |
| `message_id_hash` | TEXT    | no   | Hash of the Message-ID header                                                        |
| `user_id`         | INTEGER | yes  | `users.id` of the sender; NULL when the From field gave neither a name nor an email  |
| `date`            | TEXT    | yes  | `YYYY-MM-DD`; NULL when the Date header could not be parsed                          |
| `body_hash`       | TEXT    | yes  | Hash of the message body; NULL when the body is empty. The body itself is not stored  |

`users`, one row per (name, email) pair:

| Column       | Type    | Null | Description                                        |
| ------------ | ------- | ---- | -------------------------------------------------- |
| `id`         | INTEGER | no   | Row id, referenced by `messages.user_id`            |
| `name_hash`  | TEXT    | yes  | Hash of the display name; NULL when there is none   |
| `email_hash` | TEXT    | yes  | Hash of the lowercased address; NULL when there is none |

A sender who posted in both archives is a row in each database, under a
different id, so an id only means anything together with the archive it was read
from. The two rows carry the same hashes, which is what the comparisons match a
user on.

`message_references`, one row per (message, referenced id) pair from the References header:

| Column               | Type    | Null | Description                                                                     |
| -------------------- | ------- | ---- | ------------------------------------------------------------------------------- |
| `message_row_id`     | INTEGER | no   | `messages.id` of the referring message                                          |
| `referenced_id_hash` | TEXT    | no   | Hash of the referenced message id. Joins to `messages.message_id_hash` when that message is in the archives |

### Row counts

Built from both archives in full:

| Table                | `ia.db`    | `nb.db`   |
| -------------------- | ---------- | --------- |
| `messages`           | 5 981 974  | 613 016   |
| `users`              | 236 756    | 49 335    |
| `message_references` | 25 230 944 | 2 151 810 |

## Reading the two together

The analysis scripts read both files through `connect_archives`, which attaches
them under their archive names and reads `messages`, `users` and
`message_references` as views over the two, each row carrying the `archive` it
came from. That is what lets a comparison between the archives be one query,
and the date-filtered IA subset be a WHERE clause instead of a copy on disk.

## Checking a database built somewhere else

A message's position in its mbox file is its row id minus the lowest row id of its
newsgroup, so the ids are not just labels: the replacement-character pairs
and the embeddings both use them to find bodies. Two databases holding the same messages
under different ids will read the wrong bodies without reporting anything wrong, because
the message counts still agree.

[02_fingerprint_databases.py](02_fingerprint_databases.py) prints a fingerprint of the rows
themselves rather than of the .db files, which are not byte-reproducible between builds. Run
it on each machine and compare the output. It reads the databases read-only, and uses nothing
outside the standard library, so it can be copied to a machine that has neither this
repository nor its dependencies.

It hashes the rows of both archives twice: once as they are with the row ids included, and
once with the ids left out, ordered by their contents instead. If every line of the first
matches, the two sets of databases are interchangeable. The second is what a difference is
read against: the build hands out row ids per mbox file in the order the files are read, so
a build that read them in another order holds the same messages under different ids, and
says so by matching there while the first differs.

Both hashes go into `data/output/02_build_database/fingerprint_databases.csv`, a CSV of
`label`, `value` and `count`, with every label naming the archive it came from. Every label
is written on every run, since a hash means nothing except against the one an earlier run
wrote. When the file is already there it is read before it is rewritten, and every label
whose value or count changed is printed as `before -> after`, followed by one line per
changed table saying whether its rows differ or only their ids.

## Checking the NB database against the source files

The NB sources hold one message per file, so counting those files gives a message count that
owes nothing to the database or to the mbox files it was built from. The IA sources are mbox
files themselves, so they have no equivalent count to check against.

[03_compare_nb_database_against_source_files.py](03_compare_nb_database_against_source_files.py)
walks `data/input/nb/unzipped_data` the way
[02_parse_nb_archive.py](../01_extract_and_parse_usenet_data/02_parse_nb_archive.py) does,
counting the source files behind each mbox file stem, and compares that against
`SELECT newsgroup, COUNT(*) FROM messages` in `nb.db`. Cut-off newsgroup names are corrected
from `cut_off_newsgroup_names.csv` first, so a stem is counted under the name the mbox file,
and thus the `newsgroup` column, carries.

Both counts per newsgroup go to `data/output/02_build_database/nb_source_file_counts.csv`, a
CSV of `newsgroup`, `source_files` and `rows`. Every newsgroup whose two counts differ is
printed, and the script exits non-zero when any of them does. Both counts are currently
613 016 messages, and every one of the 139 newsgroups matches.

[05_sanity_check_nb_message_count.py](../01_extract_and_parse_usenet_data/05_sanity_check_nb_message_count.py)
makes the same comparison against the mbox files rather than the database.

## The message id hash of each source file

[04_list_nb_source_files_with_message_id_hashes.py](04_list_nb_source_files_with_message_id_hashes.py)
walks `data/input/nb/unzipped_data` the same way, and pairs each source file with the row it
was read into: the files behind an mbox file stem come back in the order the parse appended
them, so the file at a position holds the message the row at that position in `nb.db` was
built from. The hash is read out of the database rather than made again, so it is the value
the analyses join on.

The rows go to `data/output/02_build_database/nb_source_file_message_ids.csv`, a CSV of `cd`,
`source_file` and `message_id_hash`: the directory below `unzipped_data` the message came off,
its path below `unzipped_data`, and the hash of its Message-ID. The script exits non-zero
without writing anything when a newsgroup's source file and row counts differ, since the two
cannot be paired then. It currently writes one row for each of the 613 016 messages.
