"""Check that nb.db holds one row per NB source file.

The NB sources hold one message per file, so counting the files gives a message
count that owes nothing to the database or to the mbox files it was built from.
This counts the source files behind each mbox file stem, and compares that
against the rows nb.db holds per newsgroup.

Writes the per-newsgroup counts to a CSV, and exits non-zero when the two
disagree.
"""

import argparse
import csv
import logging
import sqlite3
from pathlib import Path

from usenet_no.archives.parse_nb_archive import (
    count_source_files_per_newsgroup,
    load_newsgroup_corrections,
)
from usenet_no.database import connect

logger = logging.getLogger(__name__)


def count_rows_per_newsgroup(connection: sqlite3.Connection) -> dict[str, int]:
    """The number of message rows the database holds per newsgroup."""
    return dict(
        connection.execute(
            "SELECT newsgroup, COUNT(*) FROM messages GROUP BY newsgroup"
        )
    )


def compare_counts(
    source_files: dict[str, int], rows: dict[str, int]
) -> list[tuple[str, int, int]]:
    """Pair every newsgroup of either count with its (source files, rows), sorted by name."""
    return [
        (newsgroup, source_files.get(newsgroup, 0), rows.get(newsgroup, 0))
        for newsgroup in sorted(set(source_files) | set(rows))
    ]


def export_counts_to_csv(counts: list[tuple[str, int, int]], output_file: Path) -> None:
    output_file.parent.mkdir(parents=True, exist_ok=True)
    with output_file.open("w", newline="", encoding="utf-8") as file:
        writer = csv.writer(file)
        writer.writerow(["newsgroup", "source_files", "rows"])
        writer.writerows(counts)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Check the NB database row counts against the source file counts",
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
        default=Path("data/output/02_build_database/nb_source_file_counts.csv"),
        help="CSV to write the source file and row count of each newsgroup to",
    )

    args = parser.parse_args()
    logging.basicConfig(level=logging.INFO)
    logger.info("Args: %s", args)

    corrections = load_newsgroup_corrections(args.newsgroup_corrections)
    source_files = count_source_files_per_newsgroup(args.unzipped_dir, corrections)

    connection = connect(args.nb_database_file)
    rows = count_rows_per_newsgroup(connection)
    connection.close()

    counts = compare_counts(source_files, rows)
    export_counts_to_csv(counts, args.output_file)
    logger.info("Wrote %s", args.output_file)

    total_sources = sum(source_files.values())
    total_rows = sum(rows.values())
    logger.info("Source files: %d", total_sources)
    logger.info("Rows in %s: %d", args.nb_database_file.name, total_rows)

    differing = [
        (newsgroup, expected, found)
        for newsgroup, expected, found in counts
        if expected != found
    ]
    if not differing:
        logger.info("Every one of the %d newsgroups matches", len(counts))
        raise SystemExit(0)

    for newsgroup, expected, found in differing:
        logger.error(
            "%s: %d source files, %d rows (%+d)",
            newsgroup,
            expected,
            found,
            found - expected,
        )
    logger.error(
        "%d of %d newsgroups differ, %+d messages in total",
        len(differing),
        len(counts),
        total_rows - total_sources,
    )
    raise SystemExit(1)
