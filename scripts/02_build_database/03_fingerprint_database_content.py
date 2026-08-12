"""Separate a difference in the data from a difference in how ids were assigned.

fingerprint_db.py hashes rows as they are, ids included. When two builds differ,
this says whether the contents differ too, or only the ids they were given: the
build assigns row ids per mbox file in the order the files are read, so a
different order gives every table a different fingerprint from the same data.

The fingerprint is written to a CSV. When one is already there, it is read
first and every label that changed is printed before the file is rewritten.
"""

import argparse
import csv
import hashlib
import sqlite3
from pathlib import Path

QUERIES = {
    "messages per file": "SELECT archive, newsgroup, COUNT(*) FROM messages"
    " GROUP BY archive, newsgroup ORDER BY archive, newsgroup",
    "messages, no ids": "SELECT archive, newsgroup, message_id_hash, date, body_hash"
    " FROM messages ORDER BY archive, newsgroup, message_id_hash, date, body_hash",
    "users, no ids": "SELECT name_hash, email_hash FROM users"
    " ORDER BY name_hash, email_hash",
}


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
        print(f"  {label:<22} {before_text}  ->  {' '.join(after).strip()}")


def report(database_file: Path, queries: dict[str, str]) -> list[tuple[str, str, str]]:
    """Print the id-free fingerprints and the file order, and return them as CSV rows."""
    connection = sqlite3.connect(f"file:{database_file}?mode=ro", uri=True)

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
    first_three = ", ".join(f"{a}/{n}" for a, n in order[:3])
    last_three = ", ".join(f"{a}/{n}" for a, n in order[-3:])
    print(f"  {'processing order':<22} {digest.hexdigest()}  {len(order)} files")
    print(f"  {'first three':<22} {first_three}")
    print(f"  {'last three':<22} {last_three}")

    fingerprint = [
        ("processing order", digest.hexdigest(), str(len(order))),
        ("first three", first_three, ""),
        ("last three", last_three, ""),
    ]

    for label, query in queries.items():
        rows, table_digest = hash_rows(connection, query)
        print(f"  {label:<22} {table_digest}  {rows} rows")
        fingerprint.append((label, table_digest, str(rows)))

    connection.close()
    return fingerprint


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Report whether two builds differ in their data or only in their ids",
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
        default=Path("data/output/02_build_database/fingerprint_database_content.csv"),
        help="CSV to compare against and then write the fingerprint to",
    )
    args = parser.parse_args()

    previous = read_previous_fingerprint(args.output_file)
    fingerprint = report(args.database_file, QUERIES)

    if previous:
        print(f"\nAgainst the fingerprint already in {args.output_file}:")
        print_changes(previous, fingerprint)

    args.output_file.parent.mkdir(parents=True, exist_ok=True)
    export_fingerprint_to_csv(fingerprint, args.output_file)
    print(f"\nWrote {args.output_file}")
