"""Counting body conflicts that come down to U+FFFD replacement characters in IA.

The IA data lost the Norwegian characters æ, ø and å to the Unicode replacement
character U+FFFD (�). For every newsgroup, the message ids held by both
archives without a body in common (see
`usenet_no.database.conflicts.find_newsgroup_body_conflicts`) are counted, and
their body texts are read from the mbox files to count how many conflicts have
an IA body containing U+FFFD, and how many become equal once æ/ø/å/Æ/Ø/Å in the
NB body and U+FFFD in the IA body are all replaced with "_".

The same read gives the pairs themselves: `iter_replacement_char_pairs` yields
the damaged IA body together with the intact NB body it matches, whitespace
normalized so that U+FFFD is all that separates the two texts. That is the
evaluation set `usenet_no.replacement_chars.robustness` uses.

The conflicts and their id spans come from the database, but that read is kept
out of this module: `usenet_no.database.replacement_chars` fetches them and
calls in here, so this module only reads mbox files and compares text.
"""

from collections.abc import Iterator
from dataclasses import dataclass
from itertools import groupby
from operator import attrgetter
from pathlib import Path

from tqdm import tqdm

from usenet_no.database.conflicts import NewsgroupBodyConflict
from usenet_no.database.core import IA_ARCHIVE, NB_ARCHIVE
from usenet_no.mbox_utils import get_message_bodies_at_positions
from usenet_no.text_normalization import normalize_whitespace

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


@dataclass
class ReplacementCharPair:
    """One damaged IA body and the intact NB body it matches after char replacement.

    The two bodies are the same posting, differing only in that the IA copy lost
    some of æ/ø/å/Æ/Ø/Å to U+FFFD.

    Both are stored whitespace-normalized, the same way
    `bodies_equal_with_char_replacement` compares them, since the archives wrap
    and space the same posting differently.
    """

    newsgroup: str
    message_id_hash: str
    nb_body: str
    ia_body: str
    replacement_char_count: int


# One conflict with the distinct bodies its copies hold in NB and in IA
ConflictBodies = tuple[NewsgroupBodyConflict, list[str], list[str]]


def bodies_equal_with_char_replacement(nb_body: str, ia_body: str) -> bool:
    """True when the bodies agree once æ/ø/å/Æ/Ø/Å (NB) and U+FFFD (IA) become "_".

    Whitespace is normalized on both sides first, so a difference in wrapping or
    line endings does not count as a disagreement.
    """
    return normalize_whitespace(nb_body.translate(_NB_TABLE)) == normalize_whitespace(
        ia_body.translate(_IA_TABLE)
    )


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


def _conflict_bodies_for_newsgroup(
    newsgroup: str,
    newsgroup_conflicts: list[NewsgroupBodyConflict],
    id_spans: IdSpans,
    ia_directory: Path,
    nb_directory: Path,
) -> list[ConflictBodies]:
    """Read one newsgroup's conflict bodies from its two mbox files."""
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
    return [
        (
            conflict,
            _conflict_bodies_in_archive(conflict, NB_ARCHIVE, bodies_by_row_id),
            _conflict_bodies_in_archive(conflict, IA_ARCHIVE, bodies_by_row_id),
        )
        for conflict in newsgroup_conflicts
    ]


def _iter_conflict_bodies_per_newsgroup(
    conflicts: list[NewsgroupBodyConflict],
    id_spans: IdSpans,
    ia_directory: Path,
    nb_directory: Path,
    show_progress: bool,
) -> Iterator[tuple[str, list[ConflictBodies]]]:
    """Yield each newsgroup with the bodies of its conflicts, one mbox pair at a time.

    `conflicts` must be sorted by newsgroup, as `find_newsgroup_body_conflicts`
    returns them. Newsgroups without any conflict never come up.
    """
    conflicts_by_newsgroup = [
        (newsgroup, list(newsgroup_conflicts))
        for newsgroup, newsgroup_conflicts in groupby(
            conflicts, key=attrgetter("newsgroup")
        )
    ]
    for newsgroup, newsgroup_conflicts in tqdm(
        conflicts_by_newsgroup,
        desc="Reading conflict bodies per newsgroup",
        disable=not show_progress,
    ):
        yield (
            newsgroup,
            _conflict_bodies_for_newsgroup(
                newsgroup, newsgroup_conflicts, id_spans, ia_directory, nb_directory
            ),
        )


def _counts_for_newsgroup(
    newsgroup: str, conflict_bodies: list[ConflictBodies]
) -> NewsgroupReplacementCharCounts:
    """Count one newsgroup's conflicts by their U+FFFD involvement."""
    return NewsgroupReplacementCharCounts(
        newsgroup=newsgroup,
        message_body_conflict=len(conflict_bodies),
        ia_contains_replacement_char=sum(
            any(REPLACEMENT_CHAR in ia_body for ia_body in ia_bodies)
            for _, _, ia_bodies in conflict_bodies
        ),
        equal_with_char_replacement=sum(
            any(
                bodies_equal_with_char_replacement(nb_body, ia_body)
                for nb_body in nb_bodies
                for ia_body in ia_bodies
            )
            for _, nb_bodies, ia_bodies in conflict_bodies
        ),
    )


def _first_pair_for_conflict(
    conflict_bodies: ConflictBodies,
) -> ReplacementCharPair | None:
    """The conflict's first NB/IA body pair that differs only in U+FFFD, if any.

    A conflict holds one body per distinct version per archive, so several
    combinations can match. Only the first is kept, so one conflicting message
    id contributes one pair, as `_counts_for_newsgroup` also counts it once.
    """
    conflict, nb_bodies, ia_bodies = conflict_bodies
    for ia_body in ia_bodies:
        if REPLACEMENT_CHAR not in ia_body:
            continue
        for nb_body in nb_bodies:
            if bodies_equal_with_char_replacement(nb_body, ia_body):
                normalized_ia_body = normalize_whitespace(ia_body)
                return ReplacementCharPair(
                    newsgroup=conflict.newsgroup,
                    message_id_hash=conflict.message_id_hash,
                    nb_body=normalize_whitespace(nb_body),
                    ia_body=normalized_ia_body,
                    replacement_char_count=normalized_ia_body.count(REPLACEMENT_CHAR),
                )
    return None


def count_conflicts_in_mbox_files(
    conflicts: list[NewsgroupBodyConflict],
    id_spans: IdSpans,
    ia_directory: Path,
    nb_directory: Path,
    show_progress: bool = True,
) -> list[NewsgroupReplacementCharCounts]:
    """Count per newsgroup how many of the body conflicts involve U+FFFD in the IA copy.

    `conflicts` must be sorted by newsgroup, as `find_newsgroup_body_conflicts`
    returns them. Newsgroups without any conflict are left out. Within a
    conflict, a check holds when any pair of the distinct IA and NB bodies
    satisfies it.
    """
    return [
        _counts_for_newsgroup(newsgroup, conflict_bodies)
        for newsgroup, conflict_bodies in _iter_conflict_bodies_per_newsgroup(
            conflicts, id_spans, ia_directory, nb_directory, show_progress
        )
    ]


def iter_replacement_char_pairs(
    conflicts: list[NewsgroupBodyConflict],
    id_spans: IdSpans,
    ia_directory: Path,
    nb_directory: Path,
    show_progress: bool = True,
) -> Iterator[ReplacementCharPair]:
    """Yield the body pairs whose only disagreement is U+FFFD in the IA copy.

    These are the conflicts counted in
    `NewsgroupReplacementCharCounts.equal_with_char_replacement`, yielded with
    their two body texts instead of as a count, whitespace-normalized, one pair
    per conflicting message id. `conflicts` must be sorted by newsgroup, and the
    pairs follow that order.

    Yielded rather than returned as a list: the archive holds hundreds of
    thousands of these, so a caller that samples them never has to hold more
    than one newsgroup's body texts at a time.
    """
    for _, conflict_bodies in _iter_conflict_bodies_per_newsgroup(
        conflicts, id_spans, ia_directory, nb_directory, show_progress
    ):
        for pair in map(_first_pair_for_conflict, conflict_bodies):
            if pair is not None:
                yield pair
