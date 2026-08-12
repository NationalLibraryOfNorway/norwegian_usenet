# Step 02: loading both archives into the database

- [01_build_database.py](01_build_database.py) reads the .mbox files of both archives and writes `data/output/02_build_database/usenet.db` in one pass. It holds one row per message, with names, emails and message ids as hashes only, so it can be shared.

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
