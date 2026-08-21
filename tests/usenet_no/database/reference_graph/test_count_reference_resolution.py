from usenet_no.database import IA_ARCHIVE, NB_ARCHIVE
from usenet_no.database.reference_graph import count_reference_resolution

NB = (NB_ARCHIVE, None)
IA = (IA_ARCHIVE, None)


def test_the_three_groups_add_up_to_the_total(mbox_data, load_archives):
    """One reference resolves in NB, one only in IA, and two resolve nowhere."""
    connection = load_archives(
        [
            (mbox_data / "nb/no.nb.citations.mbox", NB_ARCHIVE),
            (mbox_data / "nb/no.id.overlap.mbox", NB_ARCHIVE),
            (mbox_data / "ia/no.id.overlap.mbox", IA_ARCHIVE),
        ],
    )

    resolution = count_reference_resolution(connection, NB, IA)

    assert resolution.total == 3
    assert resolution.resolved_in_archive == 0
    assert resolution.resolved_in_other_archive == 1
    assert resolution.unresolved == 2
    assert (
        resolution.resolved_in_archive
        + resolution.resolved_in_other_archive
        + resolution.unresolved
        == resolution.total
    )


def test_a_target_nb_holds_itself_is_resolved(mbox_data, load_archives):
    """The cited origin is in NB too, so the reference resolves in NB."""
    connection = load_archives(
        [
            (mbox_data / "nb/no.graph.late.reply.mbox", NB_ARCHIVE),
            (mbox_data / "ia/no.graph.origins.mbox", NB_ARCHIVE),
        ],
    )

    resolution = count_reference_resolution(connection, NB, IA)

    assert resolution == (1, 1, 0, 0)


def test_a_target_in_both_archives_counts_as_resolved_in_nb(mbox_data, load_archives):
    """The cited message is in NB and in IA, and only the NB group counts it."""
    connection = load_archives(
        [
            (mbox_data / "nb/no.graph.dup.target.mbox", NB_ARCHIVE),
            (mbox_data / "ia/no.graph.dup.target.mbox", IA_ARCHIVE),
            (mbox_data / "ia/no.graph.cites.dup.mbox", NB_ARCHIVE),
        ],
    )

    resolution = count_reference_resolution(connection, NB, IA)

    assert resolution == (1, 1, 0, 0)


def test_the_newsgroup_is_disregarded(mbox_data, load_archives):
    """The same reply is held by two newsgroups, and its reference counts once."""
    connection = load_archives(
        [
            (mbox_data / "ia/no.graph.origins.mbox", NB_ARCHIVE),
            (mbox_data / "ia/no.graph.xpost.here.mbox", NB_ARCHIVE),
            (mbox_data / "ia/no.graph.xpost.there.mbox", NB_ARCHIVE),
        ],
    )

    resolution = count_reference_resolution(connection, NB, IA)

    assert resolution == (1, 1, 0, 0)


def test_references_within_a_newsgroup_are_counted(mbox_data, load_archives):
    """A thread citing its own newsgroup makes no graph edge, but the reference counts."""
    connection = load_archives(
        [(mbox_data / "ia/no.graph.internal.thread.mbox", NB_ARCHIVE)]
    )

    resolution = count_reference_resolution(connection, NB, IA)

    assert resolution == (1, 1, 0, 0)


def test_the_same_message_in_both_archives_counts_once(mbox_data, load_archives):
    """NB and IA hold the same reply, and NB's copy is the only referring message."""
    connection = load_archives(
        [
            (mbox_data / "ia/no.graph.origins.mbox", NB_ARCHIVE),
            (mbox_data / "nb/no.graph.same.reply.mbox", NB_ARCHIVE),
            (mbox_data / "ia/no.graph.same.reply.mbox", IA_ARCHIVE),
        ],
    )

    resolution = count_reference_resolution(connection, NB, IA)

    assert resolution == (1, 1, 0, 0)


def test_a_repeated_id_in_one_references_list_counts_once(mbox_data, load_archives):
    connection = load_archives(
        [
            (mbox_data / "ia/no.graph.origins.mbox", NB_ARCHIVE),
            (mbox_data / "ia/no.graph.stutter.mbox", NB_ARCHIVE),
        ],
    )

    resolution = count_reference_resolution(connection, NB, IA)

    assert resolution == (1, 1, 0, 0)


def test_ia_references_are_left_out(mbox_data, load_archives):
    """Only the archive whose references are counted contributes referring messages."""
    connection = load_archives(
        [
            (mbox_data / "nb/no.nb.citations.mbox", NB_ARCHIVE),
            (mbox_data / "ia/no.ia.citations.mbox", IA_ARCHIVE),
        ],
    )

    resolution = count_reference_resolution(connection, NB, IA)

    assert resolution.total == 3


def test_an_archive_without_references_counts_nothing(mbox_data, load_archives):
    connection = load_archives([(mbox_data / "ia/no.graph.origins.mbox", NB_ARCHIVE)])

    resolution = count_reference_resolution(connection, NB, IA)

    assert resolution == (0, 0, 0, 0)


def test_the_date_span_decides_what_resolves(mbox_data, load_archives):
    """A target outside the other archive's span stops being resolved by it."""
    connection = load_archives(
        [
            (mbox_data / "nb/no.graph.late.reply.mbox", NB_ARCHIVE),
            (mbox_data / "ia/no.graph.origins.mbox", IA_ARCHIVE),
        ],
    )

    unfiltered = count_reference_resolution(connection, NB, IA)
    filtered = count_reference_resolution(
        connection, NB, (IA_ARCHIVE, ("2020-01-01", "2020-12-31"))
    )

    assert unfiltered == (1, 0, 1, 0)
    assert filtered == (1, 0, 0, 1)
