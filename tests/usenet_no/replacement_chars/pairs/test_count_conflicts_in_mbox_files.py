"""count_conflicts_in_mbox_files needs no database: the conflicts and id spans
are built by hand, pointing into the sample mbox files by position."""

from usenet_no.database import IA_ARCHIVE, NB_ARCHIVE
from usenet_no.database.conflicts import NewsgroupBodyConflict
from usenet_no.replacement_chars.pairs import count_conflicts_in_mbox_files

NEWSGROUP = "no.replacement.chars"

# The ia file holds 5 messages (padding, damaged, damaged-and-rewritten,
# rewritten, identical), the nb file the same without the padding message.
# Spans start at arbitrary ids to show that only the offset matters.
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


def test_counts_hand_built_conflicts(mbox_data):
    (counts,) = count_conflicts_in_mbox_files(
        CONFLICTS,
        ID_SPANS,
        ia_directory=mbox_data / "ia",
        nb_directory=mbox_data / "nb",
        show_progress=False,
    )

    assert counts.newsgroup == NEWSGROUP
    assert counts.message_body_conflict == 3
    assert counts.ia_contains_replacement_char == 2
    assert counts.equal_with_char_replacement == 1


def test_no_conflicts_count_nothing(mbox_data):
    assert (
        count_conflicts_in_mbox_files(
            [],
            ID_SPANS,
            ia_directory=mbox_data / "ia",
            nb_directory=mbox_data / "nb",
            show_progress=False,
        )
        == []
    )
