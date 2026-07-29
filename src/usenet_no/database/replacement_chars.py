"""The connection-facing entry to the U+FFFD replacement-character analysis.

Reads the body conflicts from the database (see
`usenet_no.database.conflicts.load_conflicts_and_id_spans`) and hands them to
`usenet_no.replacement_chars.pairs`, which reads the body texts from the mbox
files and does the counting, or returns the matching body pairs.
"""

import sqlite3
from collections.abc import Iterator
from pathlib import Path

from usenet_no.database.conflicts import load_conflicts_and_id_spans
from usenet_no.replacement_chars.pairs import (
    NewsgroupReplacementCharCounts,
    ReplacementCharPair,
    count_conflicts_in_mbox_files,
    iter_replacement_char_pairs,
)


def count_replacement_char_conflicts(
    connection: sqlite3.Connection,
    ia_directory: Path,
    nb_directory: Path,
    show_progress: bool = True,
) -> list[NewsgroupReplacementCharCounts]:
    """Read the per-newsgroup conflicts from the database and count them in the mbox files."""
    conflicts, id_spans = load_conflicts_and_id_spans(connection)
    return count_conflicts_in_mbox_files(
        conflicts, id_spans, ia_directory, nb_directory, show_progress=show_progress
    )


def load_replacement_char_pairs(
    connection: sqlite3.Connection,
    ia_directory: Path,
    nb_directory: Path,
    show_progress: bool = True,
) -> Iterator[ReplacementCharPair]:
    """Read the messages with conflicts from the database"""
    conflicts, id_spans = load_conflicts_and_id_spans(connection)
    return iter_replacement_char_pairs(
        conflicts, id_spans, ia_directory, nb_directory, show_progress=show_progress
    )
