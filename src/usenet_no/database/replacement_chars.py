"""The connection-facing entry to the U+FFFD replacement-character analysis.

Reads the body conflicts from the database (see
`usenet_no.database.conflicts.load_conflicts_and_id_spans`) and hands them to
`usenet_no.replacement_chars`, which reads the body texts from the mbox files
and does the counting.
"""

import sqlite3
from pathlib import Path

from usenet_no.database.conflicts import load_conflicts_and_id_spans
from usenet_no.replacement_chars import (
    NewsgroupReplacementCharCounts,
    count_conflicts_in_mbox_files,
)


def count_replacement_char_conflicts(
    connection: sqlite3.Connection,
    ia_directory: Path,
    nb_directory: Path,
    show_progress: bool = True,
) -> list[NewsgroupReplacementCharCounts]:
    """Read the conflicts from the database and count them in the mbox files."""
    conflicts, id_spans = load_conflicts_and_id_spans(connection)
    return count_conflicts_in_mbox_files(
        conflicts, id_spans, ia_directory, nb_directory, show_progress=show_progress
    )
