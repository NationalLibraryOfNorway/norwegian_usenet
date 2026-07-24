"""Counting body conflicts that come down to U+FFFD replacement characters in IA.

The IA data lost the Norwegian characters æ, ø and å to the Unicode replacement
character U+FFFD (�). For every newsgroup, the message ids held by both
archives without a body in common (see
`usenet_no.database.conflicts.find_newsgroup_body_conflicts`) are counted, and
their body texts are read from the mbox files to count how many conflicts have
an IA body containing U+FFFD, and how many become equal once æ/ø/å/Æ/Ø/Å in the
NB body and U+FFFD in the IA body are all replaced with "_".

The conflicts and their id spans come from the database, but that read is kept
out of this module: `usenet_no.database.replacement_chars` fetches them and
calls in here, so this module only reads mbox files and compares text.
"""

from dataclasses import dataclass
from itertools import groupby
from operator import attrgetter
from pathlib import Path

from tqdm import tqdm

from usenet_no.database.conflicts import NewsgroupBodyConflict
from usenet_no.database.core import IA_ARCHIVE, NB_ARCHIVE
from usenet_no.mbox_utils import get_message_bodies_at_positions

REPLACEMENT_CHAR = "\N{REPLACEMENT CHARACTER}"
NORWEGIAN_CHARS = "æøåÆØÅ"

_NB_TABLE = str.maketrans({char: "_" for char in NORWEGIAN_CHARS})
_IA_TABLE = str.maketrans({REPLACEMENT_CHAR: "_"})

IdSpans = dict[tuple[str, str], tuple[int, int]]


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


def _conflict_bodies_in_archive(
    conflict: NewsgroupBodyConflict,
    archive: str,
    bodies_by_row_id: dict[str, dict[int, str]],
) -> list[str]:
    """The distinct bodies of one conflict's copies in one archive."""
    return [
        bodies_by_row_id[archive][row_id]
        for row_id in conflict.row_ids_per_archive[archive]
    ]


def _replacement_char_counts_for_newsgroup(
    newsgroup: str,
    newsgroup_conflicts: list[NewsgroupBodyConflict],
    id_spans: IdSpans,
    ia_directory: Path,
    nb_directory: Path,
) -> NewsgroupReplacementCharCounts:
    """Read one newsgroup's conflict bodies from its two mbox files and count them."""
    bodies_by_row_id = {
        archive: _load_conflict_bodies(
            newsgroup_conflicts,
            archive,
            directory / f"{newsgroup}.mbox",
            id_spans[(archive, newsgroup)],
        )
        for archive, directory in (
            (IA_ARCHIVE, ia_directory),
            (NB_ARCHIVE, nb_directory),
        )
    }
    conflict_bodies = [
        (
            _conflict_bodies_in_archive(conflict, NB_ARCHIVE, bodies_by_row_id),
            _conflict_bodies_in_archive(conflict, IA_ARCHIVE, bodies_by_row_id),
        )
        for conflict in newsgroup_conflicts
    ]

    return NewsgroupReplacementCharCounts(
        newsgroup=newsgroup,
        message_body_conflict=len(newsgroup_conflicts),
        ia_contains_replacement_char=sum(
            any(REPLACEMENT_CHAR in ia_body for ia_body in ia_bodies)
            for _, ia_bodies in conflict_bodies
        ),
        equal_with_char_replacement=sum(
            any(
                bodies_equal_with_char_replacement(nb_body, ia_body)
                for nb_body in nb_bodies
                for ia_body in ia_bodies
            )
            for nb_bodies, ia_bodies in conflict_bodies
        ),
    )


def count_conflicts_in_mbox_files(
    conflicts: list[NewsgroupBodyConflict],
    id_spans: IdSpans,
    ia_directory: Path,
    nb_directory: Path,
    show_progress: bool = True,
) -> list[NewsgroupReplacementCharCounts]:
    """Count per newsgroup how many of the body conflicts involve U+FFFD in the IA copy.

    `conflicts` must be sorted by newsgroup, as
    `find_newsgroup_body_conflicts` returns them. Newsgroups without any
    conflict are left out. Within a conflict, the checks hold when any pair of
    the distinct IA and NB bodies satisfies them.
    """
    conflicts_by_newsgroup = [
        (newsgroup, list(newsgroup_conflicts))
        for newsgroup, newsgroup_conflicts in groupby(
            conflicts, key=attrgetter("newsgroup")
        )
    ]
    return [
        _replacement_char_counts_for_newsgroup(
            newsgroup, newsgroup_conflicts, id_spans, ia_directory, nb_directory
        )
        for newsgroup, newsgroup_conflicts in tqdm(
            conflicts_by_newsgroup,
            desc="Reading conflict bodies per newsgroup",
            disable=not show_progress,
        )
    ]
