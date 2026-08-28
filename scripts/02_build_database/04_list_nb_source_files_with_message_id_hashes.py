"""Write the message id hash of every NB source message file.

The NB sources hold one message per file, and the parse appends them to their
newsgroup's mbox file in a fixed order, so a source file's place in that order
is the message's position in the mbox file and thus its row in nb.db. Reading
the hashes out of the database rather than hashing the ids again gives the same
values the rest of the analysis joins on.

Writes one row per source file, and exits non-zero when a newsgroup's source
files and database rows do not line up one to one.
"""

import argparse
import csv
import logging
import sqlite3
from pathlib import Path

from usenet_no.archives.encoding import source_key
from usenet_no.archives.parse_nb_archive import (
    collect_source_files_per_newsgroup,
    load_newsgroup_corrections,
)
from usenet_no.database import connect

logger = logging.getLogger(__name__)


def read_message_id_hashes_per_newsgroup(
    connection: sqlite3.Connection,
) -> dict[str, list[str]]:
    """The message id hash of every row, per newsgroup, in row id order."""
    hashes: dict[str, list[str]] = {}
    for newsgroup, message_id_hash in connection.execute(
        "SELECT newsgroup, message_id_hash FROM messages ORDER BY id"
    ):
        hashes.setdefault(newsgroup, []).append(message_id_hash)
    return hashes


def find_misaligned_newsgroups(
    sources: dict[str, list[Path]], hashes: dict[str, list[str]]
) -> list[tuple[str, int, int]]:
    """Every newsgroup whose source file and row counts differ, as (newsgroup, files, rows)."""
    return [
        (newsgroup, len(sources.get(newsgroup, [])), len(hashes.get(newsgroup, [])))
        for newsgroup in sorted(set(sources) | set(hashes))
        if len(sources.get(newsgroup, [])) != len(hashes.get(newsgroup, []))
    ]


def map_source_files_to_hashes(
    sources: dict[str, list[Path]], hashes: dict[str, list[str]], unzipped_dir: Path
) -> list[tuple[str, str, str]]:
    """Pair each source file with its message id hash, as (CD, source file, hash).

    The CD is the directory below unzipped_dir the file came off, and the source
    file is its path below unzipped_dir.
    """
    rows = []
    for newsgroup in sorted(sources):
        for message_file, message_id_hash in zip(
            sources[newsgroup], hashes[newsgroup], strict=True
        ):
            path = source_key(message_file, unzipped_dir)
            rows.append((path.split("/")[0], path, message_id_hash))
    return rows


def export_rows_to_csv(rows: list[tuple[str, str, str]], output_file: Path) -> None:
    output_file.parent.mkdir(parents=True, exist_ok=True)
    with output_file.open("w", newline="", encoding="utf-8") as file:
        writer = csv.writer(file)
        writer.writerow(["cd", "source_file", "message_id_hash"])
        writer.writerows(rows)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Write the message id hash of every NB source message file",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument(
        "--unzipped-dir",
        type=Path,
        default=Path("data/input/nb/unzipped_data"),
        help="Directory holding the extracted NB sources, one message per file",
    )
    parser.add_argument(
        "--nb-database-file",
        type=Path,
        default=Path("data/output/02_build_database/nb.db"),
        help="Path to the SQLite database file of the NB archive",
    )
    parser.add_argument(
        "--newsgroup-corrections",
        type=Path,
        default=Path(
            "data/output/01_extract_and_parse_usenet_data/cut_off_newsgroup_names.csv"
        ),
        help="CSV mapping cut-off newsgroup names to their full names, as used by the parse",
    )
    parser.add_argument(
        "--output-file",
        type=Path,
        default=Path("data/output/02_build_database/nb_source_file_message_ids.csv"),
        help="CSV to write the CD, source file path and message id hash to",
    )

    args = parser.parse_args()
    logging.basicConfig(level=logging.INFO)
    logger.info("Args: %s", args)

    corrections = load_newsgroup_corrections(args.newsgroup_corrections)
    sources = collect_source_files_per_newsgroup(args.unzipped_dir, corrections)

    connection = connect(args.nb_database_file)
    hashes = read_message_id_hashes_per_newsgroup(connection)
    connection.close()

    misaligned = find_misaligned_newsgroups(sources, hashes)
    if misaligned:
        for newsgroup, source_files, rows in misaligned:
            logger.error(
                "%s: %d source files, %d rows (%+d)",
                newsgroup,
                source_files,
                rows,
                rows - source_files,
            )
        logger.error(
            "%d of %d newsgroups differ, so the source files cannot be paired with the rows",
            len(misaligned),
            len(set(sources) | set(hashes)),
        )
        raise SystemExit(1)

    rows = map_source_files_to_hashes(sources, hashes, args.unzipped_dir)
    export_rows_to_csv(rows, args.output_file)
    logger.info("Wrote %d source files to %s", len(rows), args.output_file)
