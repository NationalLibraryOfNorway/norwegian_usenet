"""iter_replacement_char_pairs needs no database either: the conflicts and id
spans are built by hand, pointing into the sample mbox files by position."""

from usenet_no.database import IA_ARCHIVE, NB_ARCHIVE
from usenet_no.database.conflicts import NewsgroupBodyConflict
from usenet_no.replacement_chars import REPLACEMENT_CHAR, iter_replacement_char_pairs

NEWSGROUP = "no.replacement.chars"

# The ia file holds 5 messages (padding, damaged, damaged-and-rewritten,
# rewritten, identical), the nb file the same without the padding message.
ID_SPANS = {
    (IA_ARCHIVE, NEWSGROUP): (101, 5),
    (NB_ARCHIVE, NEWSGROUP): (201, 4),
}
CONFLICTS = [
    NewsgroupBodyConflict(
        newsgroup=NEWSGROUP,
        message_id_hash="hash-of-damaged",
        row_ids_per_archive={IA_ARCHIVE: [102], NB_ARCHIVE: [201]},
    ),
    NewsgroupBodyConflict(
        newsgroup=NEWSGROUP,
        message_id_hash="hash-of-damaged-and-rewritten",
        row_ids_per_archive={IA_ARCHIVE: [103], NB_ARCHIVE: [202]},
    ),
    NewsgroupBodyConflict(
        newsgroup=NEWSGROUP,
        message_id_hash="hash-of-rewritten",
        row_ids_per_archive={IA_ARCHIVE: [104], NB_ARCHIVE: [203]},
    ),
]


def test_collects_the_pair_that_differs_only_in_the_replacement_char(mbox_data):
    # Of the three conflicts, <damaged> is the only one whose bodies agree once
    # æøåÆØÅ and U+FFFD become "_". <damaged-and-rewritten> holds U+FFFD too,
    # but its bodies say different things.
    (pair,) = iter_replacement_char_pairs(
        CONFLICTS,
        ID_SPANS,
        ia_directory=mbox_data / "ia",
        nb_directory=mbox_data / "nb",
        show_progress=False,
    )

    assert pair.newsgroup == NEWSGROUP
    assert pair.message_id_hash == "hash-of-damaged"
    assert pair.nb_body == "Blåbærsyltetøy på loffen. ØL OG PØLSER."
    assert REPLACEMENT_CHAR in pair.ia_body
    assert pair.replacement_char_count == 6


def test_bodies_are_whitespace_normalized(mbox_data):
    """Normalized on both sides, so U+FFFD is the pair's only difference."""
    (pair,) = iter_replacement_char_pairs(
        CONFLICTS,
        ID_SPANS,
        ia_directory=mbox_data / "ia",
        nb_directory=mbox_data / "nb",
        show_progress=False,
    )

    nb_masked = pair.nb_body.translate(
        str.maketrans({char: REPLACEMENT_CHAR for char in "æøåÆØÅ"})
    )

    assert nb_masked == pair.ia_body


def test_no_conflicts_yield_nothing(mbox_data):
    assert (
        list(
            iter_replacement_char_pairs(
                [],
                ID_SPANS,
                ia_directory=mbox_data / "ia",
                nb_directory=mbox_data / "nb",
                show_progress=False,
            )
        )
        == []
    )
