"""Print a content fingerprint of the two databases, to compare separate builds.

The .db files are not byte-reproducible, so this hashes the rows themselves, in
a fixed order and including the row ids, since a message's position in its mbox
file is its id minus the lowest id of its (archive, newsgroup).
"""

import argparse
import hashlib
import sqlite3
from pathlib import Path

# table -> the ORDER BY that makes the read deterministic
SHARED_TABLES = {
    "users": "id",
    "messages": "id",
    "message_references": "message_row_id, referenced_id_hash",
}
PRIVATE_TABLES = {
    "users": "id",
    "message_ids": "message_id",
}


def fingerprint_table(
    connection: sqlite3.Connection, table: str, order: str
) -> tuple[int, str]:
    """The row count and a hash over every row of one table, in `order`."""
    digest = hashlib.blake2b(digest_size=16)
    rows = 0
    for row in connection.execute(f"SELECT * FROM {table} ORDER BY {order}"):
        digest.update(
            "\x1f".join(
                "\x00" if value is None else str(value) for value in row
            ).encode("utf-8")
        )
        digest.update(b"\x1e")
        rows += 1
    return rows, digest.hexdigest()


def fingerprint_schema(connection: sqlite3.Connection) -> str:
    """A hash over the schema, so a table or index that differs is caught too."""
    digest = hashlib.blake2b(digest_size=16)
    for row in connection.execute(
        "SELECT type, name, sql FROM sqlite_master ORDER BY type, name"
    ):
        digest.update(str(row).encode("utf-8"))
    return digest.hexdigest()


def report(database_file: Path, tables: dict[str, str]) -> None:
    if not database_file.exists():
        print(f"{database_file.name}: MISSING")
        return
    connection = sqlite3.connect(f"file:{database_file}?mode=ro", uri=True)
    print(f"{database_file.name}  ({database_file.stat().st_size} bytes on disk)")
    print(f"  {'schema':<20} {fingerprint_schema(connection)}")
    for table, order in tables.items():
        rows, digest = fingerprint_table(connection, table, order)
        print(f"  {table:<20} {digest}  {rows} rows")
    connection.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Print a content fingerprint of both databases",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument(
        "--database-directory",
        type=Path,
        default=Path("data/output/02_build_database"),
        help="Directory holding usenet.db and usenet_private.db",
    )
    args = parser.parse_args()
    report(args.database_directory / "usenet.db", SHARED_TABLES)
    report(args.database_directory / "usenet_private.db", PRIVATE_TABLES)
