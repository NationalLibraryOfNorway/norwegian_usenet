"""Fingerprint each archive's database, to compare separate builds.

The .db files are not byte-reproducible, so this hashes the rows themselves,
twice: once as they are with the row ids included, and once with the ids left
out. The first says whether two builds are interchangeable; the second, read
when the first differs, says whether the difference is in the data or only in
the ids the rows were given. The build hands out row ids per mbox file in the
order the files are read, so a different order gives every table a different
fingerprint from the same data.

Both archives and both hashes go into one CSV, each label naming the archive it
came from. Every label is written on every run, since a hash means nothing
except against the one an earlier run wrote. When the file is already there, it
is read first and every label that changed is printed before the file is
rewritten.
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

# The same rows with the id columns left out, ordered by their contents instead,
# so that renumbering the rows leaves the hash alone
ID_FREE_QUERIES = {
    "messages per file": "SELECT newsgroup, COUNT(*) FROM messages"
    " GROUP BY newsgroup ORDER BY newsgroup",
    "messages, no ids": "SELECT newsgroup, message_id_hash, date, body_hash"
    " FROM messages ORDER BY newsgroup, message_id_hash, date, body_hash",
    "users, no ids": "SELECT name_hash, email_hash FROM users"
    " ORDER BY name_hash, email_hash",
}

# The id-free hash a table is read against when the table itself has changed
ID_FREE_COUNTERPART = {"messages": "messages, no ids", "users": "users, no ids"}

LABEL_WIDTH = 24


def hash_rows(connection: sqlite3.Connection, query: str) -> tuple[int, str]:
    """The row count and a hash over every row the query returns, in its order."""
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


def fingerprint_schema(connection: sqlite3.Connection) -> str:
    """A hash over the schema, so a table or index that differs is caught too."""
    digest = hashlib.blake2b(digest_size=16)
    for row in connection.execute(
        "SELECT type, name, sql FROM sqlite_master ORDER BY type, name"
    ):
        digest.update(str(row).encode("utf-8"))
    return digest.hexdigest()


def fingerprint_processing_order(
    connection: sqlite3.Connection,
) -> list[tuple[str, str, str]]:
    """Hash the order the mbox files were read in, which is the order ids were handed out."""
    order = [
        newsgroup
        for (newsgroup,) in connection.execute(
            "SELECT newsgroup FROM messages GROUP BY newsgroup ORDER BY MIN(id)"
        )
    ]
    digest = hashlib.blake2b(digest_size=16)
    for newsgroup in order:
        digest.update(f"{newsgroup}\x1e".encode())
    return [
        ("processing order", digest.hexdigest(), str(len(order))),
        ("first three", ", ".join(order[:3]), ""),
        ("last three", ", ".join(order[-3:]), ""),
    ]


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
) -> set[str]:
    """Print every label whose value or count differs from the earlier run's, and return them."""
    changes = [
        (label, previous.get(label), (value, count))
        for label, value, count in fingerprint
        if previous.get(label) != (value, count)
    ]
    if not changes:
        print("  everything matches")
        return set()
    for label, before, after in changes:
        before_text = "not in the file" if before is None else " ".join(before).strip()
        print(f"  {label:<{LABEL_WIDTH}} {before_text}  ->  {' '.join(after).strip()}")
    return {label for label, _before, _after in changes}


def print_verdicts(
    changed: set[str],
    previous: dict[str, tuple[str, str]],
    fingerprint: list[tuple[str, str, str]],
) -> None:
    """Say, for each table that changed, whether its rows differ or only their ids."""
    values = {label: (value, count) for label, value, count in fingerprint}
    for label in sorted(changed):
        archive, _, table = label.partition(" ")
        if table not in ID_FREE_COUNTERPART:
            continue
        id_free_label = f"{archive} {ID_FREE_COUNTERPART[table]}"
        if previous.get(id_free_label) == values[id_free_label]:
            print(
                f'\n  {label} differs, but "{id_free_label}" matches:'
                " the same rows under different ids"
            )
        else:
            print(
                f'\n  {label} and "{id_free_label}" both differ:'
                " the rows themselves differ"
            )


def report(database_file: Path) -> list[tuple[str, str, str]]:
    """Print the fingerprint of every table, and return it with the id-free hashes."""
    connection = sqlite3.connect(f"file:{database_file}?mode=ro", uri=True)
    print(f"{database_file.name}  ({database_file.stat().st_size} bytes on disk)")

    schema_digest = fingerprint_schema(connection)
    print(f"  {'schema':<20} {schema_digest}")
    fingerprint = [("schema", schema_digest, "")]

    for table, order in TABLES.items():
        rows, digest = hash_rows(connection, f"SELECT * FROM {table} ORDER BY {order}")
        print(f"  {table:<20} {digest}  {rows} rows")
        fingerprint.append((table, digest, str(rows)))

    # Read only when a table above differs, so they are stored rather than printed
    fingerprint.extend(fingerprint_processing_order(connection))
    for label, query in ID_FREE_QUERIES.items():
        rows, digest = hash_rows(connection, query)
        fingerprint.append((label, digest, str(rows)))

    connection.close()
    return fingerprint


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Print a content fingerprint of each archive's database",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument(
        "--ia-database-file",
        type=Path,
        default=Path("data/output/02_build_database/ia.db"),
        help="Path to the SQLite database file of the IA archive",
    )
    parser.add_argument(
        "--nb-database-file",
        type=Path,
        default=Path("data/output/02_build_database/nb.db"),
        help="Path to the SQLite database file of the NB archive",
    )
    parser.add_argument(
        "--output-file",
        type=Path,
        default=Path("data/output/02_build_database/fingerprint_databases.csv"),
        help="CSV to compare against and then write the fingerprint to",
    )
    args = parser.parse_args()

    previous = read_previous_fingerprint(args.output_file)
    databases = {"ia": args.ia_database_file, "nb": args.nb_database_file}
    fingerprint = [
        (f"{archive} {label}", value, count)
        for archive, database_file in databases.items()
        for label, value, count in report(database_file)
    ]

    if previous:
        print(f"\nAgainst the fingerprint already in {args.output_file}:")
        print_verdicts(print_changes(previous, fingerprint), previous, fingerprint)

    args.output_file.parent.mkdir(parents=True, exist_ok=True)
    export_fingerprint_to_csv(fingerprint, args.output_file)
    print(f"\nWrote {args.output_file}")
