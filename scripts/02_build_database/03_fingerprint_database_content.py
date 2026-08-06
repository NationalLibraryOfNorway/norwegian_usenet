"""Separate a difference in the data from a difference in how ids were assigned.

fingerprint_db.py hashes rows as they are, ids included. When two builds differ,
this says whether the contents differ too, or only the ids they were given: the
build assigns row ids per mbox file in the order the files are read, so a
different order gives every table a different fingerprint from the same data.
"""

import argparse
import hashlib
import sqlite3
from pathlib import Path


def hash_rows(connection: sqlite3.Connection, query: str) -> tuple[int, str]:
    digest = hashlib.blake2b(digest_size=16)
    rows = 0
    for row in connection.execute(query):
        digest.update(
            "\x1f".join(
                "\x00" if value is None else str(value) for value in row
            ).encode("utf-8")
        )
        digest.update(b"\x1e")
        rows += 1
    return rows, digest.hexdigest()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Report whether two builds differ in their data or only in their ids",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument(
        "--database-directory",
        type=Path,
        default=Path("data/output/02_build_database"),
        help="Directory holding usenet.db and usenet_private.db",
    )
    args = parser.parse_args()
    connection = sqlite3.connect(
        f"file:{args.database_directory / 'usenet.db'}?mode=ro", uri=True
    )

    # The order the mbox files were read in, which is the order ids were handed out
    order = list(
        connection.execute(
            "SELECT archive, newsgroup FROM messages"
            " GROUP BY archive, newsgroup ORDER BY MIN(id)"
        )
    )
    digest = hashlib.blake2b(digest_size=16)
    for archive, newsgroup in order:
        digest.update(f"{archive}/{newsgroup}\x1e".encode())
    print(f"  {'processing order':<22} {digest.hexdigest()}  {len(order)} files")
    print(f"  {'first three':<22} {', '.join(f'{a}/{n}' for a, n in order[:3])}")
    print(f"  {'last three':<22} {', '.join(f'{a}/{n}' for a, n in order[-3:])}")

    for label, query in [
        (
            "messages per file",
            "SELECT archive, newsgroup, COUNT(*) FROM messages"
            " GROUP BY archive, newsgroup ORDER BY archive, newsgroup",
        ),
        (
            "messages, no ids",
            "SELECT archive, newsgroup, message_id_hash, date, body_hash FROM messages"
            " ORDER BY archive, newsgroup, message_id_hash, date, body_hash",
        ),
        (
            "users, no ids",
            "SELECT name_hash, email_hash FROM users ORDER BY name_hash, email_hash",
        ),
    ]:
        rows, fingerprint = hash_rows(connection, query)
        print(f"  {label:<22} {fingerprint}  {rows} rows")
    connection.close()
