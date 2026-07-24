"""Counting body conflicts that come down to U+FFFD replacement characters in IA.

The IA data lost the Norwegian characters æ, ø and å to the Unicode replacement
character U+FFFD (�). For every newsgroup, the message ids held by both
archives without a body in common (see
`usenet_no.database.conflicts.find_newsgroup_body_conflicts`) are counted, and
their body texts are read from the mbox files to count how many conflicts have
an IA body containing U+FFFD, and how many become equal once æ/ø/å/Æ/Ø/Å in the
NB body and U+FFFD in the IA body are all replaced with "_".

The database stores no body text, only hashes, so the texts are read from the
mbox files. That read is positional: the build in step 02 inserts one mbox file
at a time with contiguous row ids in file order, so within one (archive,
newsgroup) a message's position in its mbox file is `id - MIN(id)`. Both the
contiguity and the file's message count are checked, so a database that does
not match the mbox directories fails instead of pairing up the wrong bodies.
"""

import logging
import sqlite3
from dataclasses import dataclass
from itertools import groupby
from operator import attrgetter
from pathlib import Path

from tqdm import tqdm

from usenet_no.database.conflicts import (
    NewsgroupBodyConflict,
    find_newsgroup_body_conflicts,
)
from usenet_no.database.core import IA_ARCHIVE, NB_ARCHIVE
from usenet_no.mbox_utils import get_message_bodies_at_positions

logger = logging.getLogger(__name__)

REPLACEMENT_CHAR = "\N{REPLACEMENT CHARACTER}"
NORWEGIAN_CHARS = "æøåÆØÅ"

_NB_TABLE = str.maketrans({char: "_" for char in NORWEGIAN_CHARS})
_IA_TABLE = str.maketrans({REPLACEMENT_CHAR: "_"})


@dataclass
class NewsgroupReplacementCharCounts:
    """Per-newsgroup counts of body conflicts and their U+FFFD involvement."""

    newsgroup: str
    message_body_conflict: int
    ia_contains_replacement_char: int
    equal_with_char_replacement: int


def bodies_equal_with_char_replacement(nb_body: str, ia_body: str) -> bool:
    """True when the bodies agree once æ/ø/å/Æ/Ø/Å (NB) and U+FFFD (IA) become "_"."""
    return nb_body.translate(_NB_TABLE) == ia_body.translate(_IA_TABLE)


def _load_id_spans(
    connection: sqlite3.Connection,
) -> dict[tuple[str, str], tuple[int, int]]:
    """Map each (archive, newsgroup) to its (lowest row id, message count).

    Raises when a span is not contiguous, since the positional mbox lookup
    depends on row ids following file order without gaps.
    """
    spans = {}
    for archive, newsgroup, min_id, max_id, count in connection.execute(
        "SELECT archive, newsgroup, MIN(id), MAX(id), COUNT(*)"
        " FROM messages GROUP BY archive, newsgroup"
    ):
        if max_id - min_id + 1 != count:
            raise ValueError(
                f"Row ids of ({archive}, {newsgroup}) are not contiguous:"
                f" {count} rows span ids {min_id}..{max_id}"
            )
        spans[(archive, newsgroup)] = (min_id, count)
    return spans


def _load_conflict_bodies(
    conflicts: list[NewsgroupBodyConflict],
    archive: str,
    mbox_file: Path,
    id_span: tuple[int, int],
) -> dict[int, str]:
    """Read the body of every row id the conflicts name in one archive's mbox file."""
    min_id, message_count = id_span
    row_ids = {
        row_id
        for conflict in conflicts
        for row_id in conflict.row_ids_per_archive[archive]
    }
    bodies_by_position = get_message_bodies_at_positions(
        mbox_file,
        positions=[row_id - min_id for row_id in row_ids],
        expected_message_count=message_count,
    )
    return {row_id: bodies_by_position[row_id - min_id] for row_id in row_ids}


def count_replacement_char_conflicts(
    connection: sqlite3.Connection,
    ia_directory: Path,
    nb_directory: Path,
    show_progress: bool = True,
) -> list[NewsgroupReplacementCharCounts]:
    """Count per newsgroup how many body conflicts involve U+FFFD in the IA copy.

    Newsgroups without any conflict are left out. Within a conflict, the checks
    hold when any pair of the distinct IA and NB bodies satisfies them.
    """
    conflicts = find_newsgroup_body_conflicts(connection)
    id_spans = _load_id_spans(connection)
    logger.info("Found %d body conflicts", len(conflicts))

    results = []
    grouped = [
        (newsgroup, list(newsgroup_conflicts))
        for newsgroup, newsgroup_conflicts in groupby(
            conflicts, key=attrgetter("newsgroup")
        )
    ]
    for newsgroup, newsgroup_conflicts in tqdm(
        grouped, desc="Reading conflict bodies per newsgroup", disable=not show_progress
    ):
        bodies_by_row_id = {}
        for archive, directory in (
            (IA_ARCHIVE, ia_directory),
            (NB_ARCHIVE, nb_directory),
        ):
            bodies_by_row_id[archive] = _load_conflict_bodies(
                newsgroup_conflicts,
                archive,
                directory / f"{newsgroup}.mbox",
                id_spans[(archive, newsgroup)],
            )

        ia_contains_replacement_char = 0
        equal_with_char_replacement = 0
        for conflict in newsgroup_conflicts:
            ia_bodies = [
                bodies_by_row_id[IA_ARCHIVE][row_id]
                for row_id in conflict.row_ids_per_archive[IA_ARCHIVE]
            ]
            nb_bodies = [
                bodies_by_row_id[NB_ARCHIVE][row_id]
                for row_id in conflict.row_ids_per_archive[NB_ARCHIVE]
            ]
            if any(REPLACEMENT_CHAR in ia_body for ia_body in ia_bodies):
                ia_contains_replacement_char += 1
            if any(
                bodies_equal_with_char_replacement(nb_body, ia_body)
                for nb_body in nb_bodies
                for ia_body in ia_bodies
            ):
                equal_with_char_replacement += 1

        results.append(
            NewsgroupReplacementCharCounts(
                newsgroup=newsgroup,
                message_body_conflict=len(newsgroup_conflicts),
                ia_contains_replacement_char=ia_contains_replacement_char,
                equal_with_char_replacement=equal_with_char_replacement,
            )
        )

    return results
