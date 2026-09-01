from usenet_no.database import IA_ARCHIVE
from usenet_no.database.reference_graph import (
    UNKNOWN_NEWSGROUP,
    count_referenced_messages,
)


def test_many_references_to_one_message_count_once(mbox_data, load_archives):
    """Three replies cite the same origin, which is one referenced message."""
    connection = load_archives(
        [
            (mbox_data / "ia/no.graph.origins.mbox", IA_ARCHIVE),
            (mbox_data / "ia/no.graph.replies.mbox", IA_ARCHIVE),
        ],
    )

    edges = count_referenced_messages(connection, [(IA_ARCHIVE, None)])

    assert edges == [("no.graph.replies", "no.graph.origins", 1, 1, 1)]


def test_distinct_targets_count_separately(mbox_data, load_archives):
    """One reply cites both origins, which is two referenced messages."""
    connection = load_archives(
        [
            (mbox_data / "ia/no.graph.origins.mbox", IA_ARCHIVE),
            (mbox_data / "ia/no.graph.two.targets.mbox", IA_ARCHIVE),
        ],
    )

    edges = count_referenced_messages(connection, [(IA_ARCHIVE, None)])

    assert edges == [("no.graph.two.targets", "no.graph.origins", 2, 2, 2)]


def test_each_unknown_id_counts_once(mbox_data, load_archives):
    """Three references reach messages nobody kept, but only two distinct ids."""
    connection = load_archives(
        [(mbox_data / "ia/no.graph.cites.ghosts.mbox", IA_ARCHIVE)]
    )

    edges = count_referenced_messages(connection, [(IA_ARCHIVE, None)])

    assert edges == [("no.graph.cites.ghosts", UNKNOWN_NEWSGROUP, 2, 2, 2)]


def test_references_within_a_newsgroup_make_no_edge(mbox_data, load_archives):
    connection = load_archives(
        [(mbox_data / "ia/no.graph.internal.thread.mbox", IA_ARCHIVE)]
    )

    edges = count_referenced_messages(connection, [(IA_ARCHIVE, None)])

    assert edges == []
