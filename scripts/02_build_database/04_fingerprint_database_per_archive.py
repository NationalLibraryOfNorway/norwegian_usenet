"""Split the fingerprint by archive, to locate which parse step ids came from.

The build inserts every IA file before any NB file, so a sender first seen in IA
is given its id while IA is being read. If only the NB parse ordered its messages
differently, the IA rows and the users numbered during IA should match between
two builds, and only the NB rows and the later users should differ.
"""

import argparse
import hashlib
import sqlite3
from pathlib import Path


def hash_rows(
    connection: sqlite3.Connection, query: str, parameters=()
) -> tuple[int, str]:
    digest = hashlib.blake2b(digest_size=16)
    rows = 0
    for row in connection.execute(query, parameters):
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
        description="Split the fingerprint by archive",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument(
        "--database-file",
        type=Path,
        default=Path("data/output/02_build_database/usenet.db"),
        help="Path to the SQLite database file",
    )
    args = parser.parse_args()
    connection = sqlite3.connect(f"file:{args.database_file}?mode=ro", uri=True)

    for archive in ("ia", "nb"):
        rows, digest = hash_rows(
            connection,
            "SELECT * FROM messages WHERE archive = ? ORDER BY id",
            (archive,),
        )
        print(f"  {'messages ' + archive:<26} {digest}  {rows} rows")

    # The highest user id handed out while IA was being read
    (ia_max_user_id,) = connection.execute(
        "SELECT COALESCE(MAX(user_id), 0) FROM messages WHERE archive = 'ia'"
    ).fetchone()
    print(f"  {'last user id from IA':<26} {ia_max_user_id}")

    for label, comparison in [
        ("users numbered during IA", "<="),
        ("users numbered after IA", ">"),
    ]:
        rows, digest = hash_rows(
            connection,
            f"SELECT * FROM users WHERE id {comparison} ? ORDER BY id",
            (ia_max_user_id,),
        )
        print(f"  {label:<26} {digest}  {rows} rows")

    connection.close()
