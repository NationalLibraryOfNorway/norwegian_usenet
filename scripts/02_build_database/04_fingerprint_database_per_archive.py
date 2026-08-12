"""Split the fingerprint by archive, to locate which parse step ids came from.

The build inserts every IA file before any NB file, so a sender first seen in IA
is given its id while IA is being read. If only the NB parse ordered its messages
differently, the IA rows and the users numbered during IA should match between
two builds, and only the NB rows and the later users should differ.

The fingerprint is written to a CSV. When one is already there, it is read
first and every label that changed is printed before the file is rewritten.
"""

import argparse
import csv
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
        print(f"  {label:<26} {before_text}  ->  {' '.join(after).strip()}")


def report(database_file: Path) -> list[tuple[str, str, str]]:
    """Print the per-archive fingerprints, and return them as CSV rows."""
    connection = sqlite3.connect(f"file:{database_file}?mode=ro", uri=True)
    fingerprint = []

    for archive in ("ia", "nb"):
        rows, digest = hash_rows(
            connection,
            "SELECT * FROM messages WHERE archive = ? ORDER BY id",
            (archive,),
        )
        print(f"  {'messages ' + archive:<26} {digest}  {rows} rows")
        fingerprint.append((f"messages {archive}", digest, str(rows)))

    # The highest user id handed out while IA was being read
    (ia_max_user_id,) = connection.execute(
        "SELECT COALESCE(MAX(user_id), 0) FROM messages WHERE archive = 'ia'"
    ).fetchone()
    print(f"  {'last user id from IA':<26} {ia_max_user_id}")
    fingerprint.append(("last user id from IA", str(ia_max_user_id), ""))

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
        fingerprint.append((label, digest, str(rows)))

    connection.close()
    return fingerprint


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
    parser.add_argument(
        "--output-file",
        type=Path,
        default=Path(
            "data/output/02_build_database/fingerprint_database_per_archive.csv"
        ),
        help="CSV to compare against and then write the fingerprint to",
    )
    args = parser.parse_args()

    previous = read_previous_fingerprint(args.output_file)
    fingerprint = report(args.database_file)

    if previous:
        print(f"\nAgainst the fingerprint already in {args.output_file}:")
        print_changes(previous, fingerprint)

    args.output_file.parent.mkdir(parents=True, exist_ok=True)
    export_fingerprint_to_csv(fingerprint, args.output_file)
    print(f"\nWrote {args.output_file}")
