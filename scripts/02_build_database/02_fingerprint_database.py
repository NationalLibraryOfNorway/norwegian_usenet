"""Print a content fingerprint of the database, to compare separate builds.

The .db file is not byte-reproducible, so this hashes the rows themselves, in
a fixed order and including the row ids, since a message's position in its mbox
file is its id minus the lowest id of its (archive, newsgroup).

The fingerprint is written to a CSV. When one is already there, it is read
first and every label that changed is printed before the file is rewritten.
"""

import argparse
import csv
import hashlib
import sqlite3
from pathlib import Path

# table -> the ORDER BY that makes the read deterministic
TABLES = {
    "users": "id",
    "messages": "id",
    "message_references": "message_row_id, referenced_id_hash",
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


def read_previous_fingerprint(output_file: Path) -> dict[str, tuple[str, str]]:
    """Map each label an earlier run wrote to its (value, count)."""
    if not output_file.exists():
        return {}
    with output_file.open(newline="", encoding="utf-8") as file:
        return {
            label: (value, count) for label, value, count in list(csv.reader(file))[1:]
        }


def export_fingerprint_to_csv(
    fingerprint: list[tuple[str, str, str]], output_file: Path
) -> None:
    with output_file.open(mode="w", newline="", encoding="utf-8") as file:
        writer = csv.writer(file)
        writer.writerow(["label", "value", "count"])
        writer.writerows(fingerprint)


def print_changes(
    previous: dict[str, tuple[str, str]], fingerprint: list[tuple[str, str, str]]
) -> None:
    """Print every label whose value or count differs from the earlier run's."""
    changes = [
        (label, previous.get(label), (value, count))
        for label, value, count in fingerprint
        if previous.get(label) != (value, count)
    ]
    if not changes:
        print("  everything matches")
        return
    for label, before, after in changes:
        before_text = "not in the file" if before is None else " ".join(before).strip()
        print(f"  {label:<20} {before_text}  ->  {' '.join(after).strip()}")


def report(database_file: Path, tables: dict[str, str]) -> list[tuple[str, str, str]]:
    """Print the fingerprint of every table, and return it as CSV rows."""
    connection = sqlite3.connect(f"file:{database_file}?mode=ro", uri=True)
    print(f"{database_file.name}  ({database_file.stat().st_size} bytes on disk)")

    schema_digest = fingerprint_schema(connection)
    print(f"  {'schema':<20} {schema_digest}")
    fingerprint = [("schema", schema_digest, "")]

    for table, order in tables.items():
        rows, digest = fingerprint_table(connection, table, order)
        print(f"  {table:<20} {digest}  {rows} rows")
        fingerprint.append((table, digest, str(rows)))

    connection.close()
    return fingerprint


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Print a content fingerprint of the database",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument(
        "--database-file",
        type=Path,
        default=Path("data/output/02_build_database/usenet.db"),
        help="Path to the SQLite database file",
    )
    parser.add_argument(
        "--output-file",
        type=Path,
        default=Path("data/output/02_build_database/fingerprint_database.csv"),
        help="CSV to compare against and then write the fingerprint to",
    )
    args = parser.parse_args()

    previous = read_previous_fingerprint(args.output_file)
    fingerprint = report(args.database_file, TABLES)

    if previous:
        print(f"\nAgainst the fingerprint already in {args.output_file}:")
        print_changes(previous, fingerprint)

    args.output_file.parent.mkdir(parents=True, exist_ok=True)
    export_fingerprint_to_csv(fingerprint, args.output_file)
    print(f"\nWrote {args.output_file}")
