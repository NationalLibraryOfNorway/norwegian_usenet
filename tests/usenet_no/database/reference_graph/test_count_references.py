from usenet_no.database import IA_ARCHIVE, NB_ARCHIVE
from usenet_no.database.reference_graph import (
    UNKNOWN_NEWSGROUP,
    count_references,
)


def test_every_reference_counts(mbox_data, load_archives):
    """Three replies cite the same origin, so the edge weighs three."""
    connection = load_archives(
        [
            (mbox_data / "ia/no.graph.origins.mbox", IA_ARCHIVE),
            (mbox_data / "ia/no.graph.replies.mbox", IA_ARCHIVE),
        ],
    )

    edges = count_references(connection, [(IA_ARCHIVE, None)])

    assert edges == [("no.graph.replies", "no.graph.origins", 3, 3, 3)]


def test_two_targets_in_one_message_count_twice(mbox_data, load_archives):
    """One reply cites both origins, so the edge weighs two."""
    connection = load_archives(
        [
            (mbox_data / "ia/no.graph.origins.mbox", IA_ARCHIVE),
            (mbox_data / "ia/no.graph.two.targets.mbox", IA_ARCHIVE),
        ],
    )

    edges = count_references(connection, [(IA_ARCHIVE, None)])

    assert edges == [("no.graph.two.targets", "no.graph.origins", 2, 2, 2)]


def test_direction_is_kept(mbox_data, load_archives):
    """Each group cites the other once, which is two edges, not one of weight two."""
    connection = load_archives(
        [
            (mbox_data / "ia/no.graph.mutual.a.mbox", IA_ARCHIVE),
            (mbox_data / "ia/no.graph.mutual.b.mbox", IA_ARCHIVE),
        ],
    )

    edges = count_references(connection, [(IA_ARCHIVE, None)])

    assert sorted(edges) == [
        ("no.graph.mutual.a", "no.graph.mutual.b", 1, 1, 1),
        ("no.graph.mutual.b", "no.graph.mutual.a", 1, 1, 1),
    ]


def test_unresolved_references_go_to_the_unknown_newsgroup(mbox_data, load_archives):
    """Two replies cite messages nobody kept: one ghost once, one ghost twice."""
    connection = load_archives(
        [(mbox_data / "ia/no.graph.cites.ghosts.mbox", IA_ARCHIVE)]
    )

    edges = count_references(connection, [(IA_ARCHIVE, None)])

    assert edges == [("no.graph.cites.ghosts", UNKNOWN_NEWSGROUP, 3, 3, 3)]


def test_references_within_a_newsgroup_make_no_edge(mbox_data, load_archives):
    connection = load_archives(
        [(mbox_data / "ia/no.graph.internal.thread.mbox", IA_ARCHIVE)]
    )

    edges = count_references(connection, [(IA_ARCHIVE, None)])

    assert edges == []


def test_a_crossposted_target_feeds_every_holding_newsgroup(mbox_data, load_archives):
    """One reference to a message held by two groups adds one to both edges."""
    connection = load_archives(
        [
            (mbox_data / "ia/no.graph.crossed.a.mbox", IA_ARCHIVE),
            (mbox_data / "ia/no.graph.crossed.b.mbox", IA_ARCHIVE),
            (mbox_data / "ia/no.graph.cites.crossed.mbox", IA_ARCHIVE),
        ],
    )

    edges = count_references(connection, [(IA_ARCHIVE, None)])

    # crossed.a's own reply to the crossposted message reaches crossed.b too,
    # while its copy in crossed.a itself is a self-loop and makes no edge.
    assert sorted(edges) == [
        ("no.graph.cites.crossed", "no.graph.crossed.a", 1, 2, 2),
        ("no.graph.cites.crossed", "no.graph.crossed.b", 1, 2, 2),
        ("no.graph.crossed.a", "no.graph.crossed.b", 1, 2, 1),
    ]


def test_a_crossposted_source_counts_from_each_newsgroup(mbox_data, load_archives):
    """The same reply is held by two groups, and each group's copy is a source."""
    connection = load_archives(
        [
            (mbox_data / "ia/no.graph.origins.mbox", IA_ARCHIVE),
            (mbox_data / "ia/no.graph.xpost.here.mbox", IA_ARCHIVE),
            (mbox_data / "ia/no.graph.xpost.there.mbox", IA_ARCHIVE),
        ],
    )

    edges = count_references(connection, [(IA_ARCHIVE, None)])

    assert sorted(edges) == [
        ("no.graph.xpost.here", "no.graph.origins", 1, 1, 1),
        ("no.graph.xpost.there", "no.graph.origins", 1, 1, 1),
    ]


def test_the_same_message_in_both_archives_counts_once(mbox_data, load_archives):
    """Both archives hold the same reply in the same group, which is one message."""
    connection = load_archives(
        [
            (mbox_data / "ia/no.graph.origins.mbox", IA_ARCHIVE),
            (mbox_data / "ia/no.graph.same.reply.mbox", IA_ARCHIVE),
            (mbox_data / "nb/no.graph.same.reply.mbox", NB_ARCHIVE),
        ],
    )

    edges = count_references(connection, [(IA_ARCHIVE, None), (NB_ARCHIVE, None)])

    assert edges == [("no.graph.same.reply", "no.graph.origins", 1, 1, 1)]


def test_a_repeated_id_in_one_references_list_counts_once(mbox_data, load_archives):
    connection = load_archives(
        [
            (mbox_data / "ia/no.graph.origins.mbox", IA_ARCHIVE),
            (mbox_data / "ia/no.graph.stutter.mbox", IA_ARCHIVE),
        ],
    )

    edges = count_references(connection, [(IA_ARCHIVE, None)])

    assert edges == [("no.graph.stutter", "no.graph.origins", 1, 1, 1)]


def test_a_target_held_by_both_archives_is_one_newsgroup(mbox_data, load_archives):
    """The cited posting is in the same group in both archives: one edge of weight one."""
    connection = load_archives(
        [
            (mbox_data / "ia/no.graph.dup.target.mbox", IA_ARCHIVE),
            (mbox_data / "nb/no.graph.dup.target.mbox", NB_ARCHIVE),
            (mbox_data / "ia/no.graph.cites.dup.mbox", IA_ARCHIVE),
        ],
    )

    edges = count_references(connection, [(IA_ARCHIVE, None), (NB_ARCHIVE, None)])

    assert edges == [("no.graph.cites.dup", "no.graph.dup.target", 1, 1, 1)]


def test_messages_without_references_make_no_edges(mbox_data, load_archives):
    connection = load_archives([(mbox_data / "ia/no.graph.origins.mbox", IA_ARCHIVE)])

    edges = count_references(connection, [(IA_ARCHIVE, None)])

    assert edges == []


def test_the_archive_scope_decides_what_resolves(mbox_data, load_archives):
    """The cited origin is held only by ia, so nb alone reads it as unknown."""
    connection = load_archives(
        [
            (mbox_data / "ia/no.graph.origins.mbox", IA_ARCHIVE),
            (mbox_data / "nb/no.graph.late.reply.mbox", NB_ARCHIVE),
        ],
    )

    nb_only = count_references(connection, [(NB_ARCHIVE, None)])
    both = count_references(connection, [(NB_ARCHIVE, None), (IA_ARCHIVE, None)])

    assert nb_only == [("no.graph.late.reply", UNKNOWN_NEWSGROUP, 1, 1, 1)]
    assert both == [("no.graph.late.reply", "no.graph.origins", 1, 1, 1)]


def test_the_date_span_is_respected(mbox_data, load_archives):
    """Replies outside the span are dropped, and targets outside it are unknown."""
    connection = load_archives(
        [
            (mbox_data / "ia/no.graph.dated.origin.mbox", IA_ARCHIVE),
            (mbox_data / "ia/no.graph.dated.replies.mbox", IA_ARCHIVE),
        ],
    )

    unfiltered = count_references(connection, [(IA_ARCHIVE, None)])
    filtered = count_references(
        connection, [(IA_ARCHIVE, ("1996-01-01", "1996-12-31"))]
    )

    assert unfiltered == [("no.graph.dated.replies", "no.graph.dated.origin", 3, 3, 3)]
    assert sorted(filtered) == [
        ("no.graph.dated.replies", "no.graph.dated.origin", 1, 2, 2),
        ("no.graph.dated.replies", UNKNOWN_NEWSGROUP, 1, 2, 2),
    ]


def test_the_totals_count_the_referring_newsgroup_with_and_without_itself(
    mbox_data, load_archives
):
    """The group makes two references, one of them within itself."""
    connection = load_archives(
        [
            (mbox_data / "ia/no.graph.origins.mbox", IA_ARCHIVE),
            (mbox_data / "ia/no.graph.mixed.thread.mbox", IA_ARCHIVE),
        ],
    )

    edges = count_references(connection, [(IA_ARCHIVE, None)])

    assert edges == [("no.graph.mixed.thread", "no.graph.origins", 1, 2, 1)]
