# Step 02: loading each archive into an SQLite database

- [01_build_databases.py](01_build_databases.py) reads the .mbox files of each archive and writes two files per archive: `ia.db` and `nb.db`, which hold one row per message, and `ia_users.db` and `nb_users.db`, which hold the addresses those messages were sent from. All four go in `data/output/02_build_database/`. Run with `--overwrite` to delete existing database files and build them again; without the flag an archive whose files are already there is skipped.
- [02_fingerprint_databases.py](02_fingerprint_databases.py) prints a fingerprint of the rows themselves rather than of the .db files, which are not byte-reproducible between builds, so that a build made elsewhere can be held up against this one. The row ids are not just labels: a message's position in its mbox file is its row id minus the lowest row id of its newsgroup, and the replacement-character pairs and the embeddings both use that to find bodies, so two databases holding the same messages under different ids read the wrong bodies without reporting anything wrong, because the message counts still agree. It reads the databases read-only and uses nothing outside the standard library, so it can be copied to a machine that has neither this repository nor its dependencies. The databases to fingerprint are given as arguments, and each is read as whichever kind its tables say it is, so a machine holding only the published files can check those on their own; with no arguments it fingerprints the two archive databases.

  ```
  python 02_fingerprint_databases.py data/output/02_build_database/{ia,nb}.db
  python 02_fingerprint_databases.py data/output/02_build_database/{ia,nb}_users.db
  ```

  - Every table is hashed as it stands, with its row ids, and if each of those matches, the two sets of databases are interchangeable. `messages`, `emails` and `email_names` are hashed a second time with the ids left out, ordered by their contents instead; `message_references` is not, holding nothing but a row id and a hash. That second hash is what a difference is read against: matching there while the first differs means the same rows under different ids.
  - An archive database also stores the order its mbox files were read in, as `processing order` with the first and last three newsgroup names beside it, and a message count per newsgroup as `messages per file`. The build hands out row ids one mbox file at a time in that order, so a build that read the files in another order holds the same messages under different ids. A user database gets no processing order of its own, though its ids follow the same reading order: an address is numbered when the build first meets it.
  - The archive databases' hashes go into `data/output/02_build_database/fingerprint_databases.csv` and the user databases' into `fingerprint_user_databases.csv` beside it, which is where each kind is written when `--output-file` is not given. Both are CSVs of `label`, `value` and `count`, with every label naming the file it came from, and both are kept in the repository: a fingerprint is a hash over a whole table rather than over each row, so testing an address against one would mean already holding every address in the archive. Every label is written on every run, since a hash means nothing except against the one an earlier run wrote. When the file is already there it is read before it is rewritten, and every label whose value or count changed is printed as `before -> after`, followed by one line per changed table saying whether its rows differ or only their ids.
- [03_compare_nb_database_against_source_files.py](03_compare_nb_database_against_source_files.py) checks that `nb.db` holds one row per NB source file. The NB sources hold one message per file, so counting those files gives a message count that owes nothing to the database or to the mbox files it was built from; the IA sources are mbox files themselves, so they have no equivalent count to check against. It walks `data/input/nb/unzipped_data` the way [02_parse_nb_archive.py](../01_extract_and_parse_usenet_data/02_parse_nb_archive.py) does, counting the source files behind each mbox file stem, and compares that against `SELECT newsgroup, COUNT(*) FROM messages` in `nb.db`. Cut-off newsgroup names are corrected from `cut_off_newsgroup_names.csv` first, so a stem is counted under the name the mbox file, and thus the `newsgroup` column, carries. Both counts per newsgroup go to `data/output/02_build_database/nb_source_file_counts.csv`, a CSV of `newsgroup`, `source_files` and `rows`. Every newsgroup whose two counts differ is printed, and the script exits non-zero when any of them does. Both counts are currently 613 016 messages, and every one of the 139 newsgroups matches. [05_sanity_check_nb_message_count.py](../01_extract_and_parse_usenet_data/05_sanity_check_nb_message_count.py) makes the same comparison against the mbox files rather than the database.
- [04_list_nb_source_files_with_message_id_hashes.py](04_list_nb_source_files_with_message_id_hashes.py) walks `data/input/nb/unzipped_data` the same way, and pairs each source file with the row it was read into: the files behind an mbox file stem come back in the order the parse appended them, so the file at a position holds the message the row at that position in `nb.db` was built from. The hash is read out of the database rather than made again, so it is the value the analyses join on. The rows go to `data/output/02_build_database/nb_source_file_message_ids.csv`, a CSV of `cd`, `source_file` and `message_id_hash`: the directory below `unzipped_data` the message came off, its path below `unzipped_data`, and the hash of its Message-ID. It currently writes one row for each of the 613 016 messages.
- [05_show_message_by_database_id.py](05_show_message_by_database_id.py) prints the message one database row was built from, envelope line and all, as the mbox file holds it, followed by the text `get_message_body` reads it as. A row's position in its newsgroup's mbox file is its id minus the lowest id of that newsgroup, so the archive and the row id locate the message on their own. It works for either archive, and is how a row whose columns look odd is read back as a message.

## The archive databases: `ia.db` and `nb.db`

These are the two files kept in the repository. Both have the same schema.
Every hash column holds a 16 character hex digest, from `blake2b` with an 8 byte digest, of the UTF-8 plain text.
A hash is traced back to its plain text through the mbox files, by the position `messages.id` gives.
The schema is in [`src/usenet_no/database/build.py`](../../src/usenet_no/database/build.py).

```sql
CREATE TABLE messages (
    id              INTEGER PRIMARY KEY,
    newsgroup       TEXT NOT NULL,
    message_id_hash TEXT NOT NULL,
    email_id        INTEGER,
    date            TEXT,
    body_hash       TEXT
);

CREATE TABLE message_references (
    message_row_id     INTEGER NOT NULL REFERENCES messages(id),
    referenced_id_hash TEXT NOT NULL
);

CREATE INDEX idx_messages_newsgroup ON messages(newsgroup);
CREATE INDEX idx_messages_message_id_hash ON messages(message_id_hash);
CREATE INDEX idx_messages_email_id ON messages(email_id);
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
| `email_id`        | INTEGER | yes  | `emails.id` of the sender in the archive's user database; NULL when the From field gave no address |
| `date`            | TEXT    | yes  | `YYYY-MM-DD`; NULL when the Date header could not be parsed                          |
| `body_hash`       | TEXT    | yes  | Hash of the message body; NULL when the body is empty. The body itself is not stored  |

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
| `message_references` | 25 230 944 | 2 151 810 |

6 822 IA messages and 1 222 NB messages have no `email_id`: the ones whose From
header gave no address at all, and the 746 and 7 whose From header gave a display
name and nothing else.

## The user databases: `ia_users.db` and `nb_users.db`

One is built beside each archive database, holding the addresses its `email_id`
column stands for. They are the only files carrying a hashed address, and
`.gitignore` keeps them out of the repository.

```sql
CREATE TABLE emails (
    id         INTEGER PRIMARY KEY,
    email_hash TEXT NOT NULL
);

CREATE TABLE email_names (
    email_id  INTEGER NOT NULL REFERENCES emails(id),
    name_hash TEXT NOT NULL
);

CREATE INDEX idx_emails_email_hash ON emails(email_hash);
CREATE INDEX idx_email_names_email_id ON email_names(email_id);
```

`emails`, one row per address:

| Column       | Type    | Null | Description                                    |
| ------------ | ------- | ---- | ---------------------------------------------- |
| `id`         | INTEGER | no   | Row id, referred to by `messages.email_id`      |
| `email_hash` | TEXT    | no   | Hash of the lowercased address                  |

`email_names`, one row per name an address posted under:

| Column      | Type    | Null | Description                        |
| ----------- | ------- | ---- | ---------------------------------- |
| `email_id`  | INTEGER | no   | `emails.id` of the address          |
| `name_hash` | TEXT    | no   | Hash of the display name            |

A sender who posted in both archives is a row in each user database, under a
different id, so an id only means anything together with the archive it was read
from. The two rows carry the same hash, which is what the comparisons match a
user on.

### Row counts

| Table         | `ia_users.db` | `nb_users.db` |
| ------------- | ------------- | ------------- |
| `emails`      | 190 136       | 42 745        |
| `email_names` | 187 598       | 27 605        |

## Reading the two together

The analysis scripts read both archives through `connect_archives`, which
attaches them under their archive names and reads `messages` and
`message_references` as views over the two, each row carrying the `archive` it
came from. That is what lets a comparison between the archives be one query,
and the date-filtered IA subset be a WHERE clause instead of a copy on disk.

A script that has to recognise a user across the two archives uses
`connect_archives_and_users` instead, which attaches the user databases as well
and adds an `emails` view over them, again carrying the `archive`. Anything
counting users within one archive needs none of that and groups on
`messages.email_id`, so most of the analysis runs on the published files alone.
