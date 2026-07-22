from usenet_no.database.comparison import compare_message_ids
from usenet_no.database import IA_ARCHIVE, NB_ARCHIVE

SPAN = ("1996-01-06", "1996-01-20")


def test_counts_message_id_overlap_between_the_archives(
    mbox_data, database, load_archives
):
    connection = load_archives(
        database,
        [
            (mbox_data / "ia/no.id.overlap.mbox", IA_ARCHIVE),
            (mbox_data / "nb/no.id.overlap.mbox", NB_ARCHIVE),
        ],
    )

    results = compare_message_ids(connection)

    assert results["ia_ids"] == 2
    assert results["nb_ids"] == 2
    assert results["ids_in_both"] == 1
    assert results["ids_ia_only"] == 1
    assert results["ids_nb_only"] == 1


def test_counts_references_the_other_archive_resolves(
    mbox_data, database, load_archives
):
    """A reply cites a posting its own archive lost but the other one kept."""
    connection = load_archives(
        database,
        [
            (mbox_data / "ia/no.id.overlap.mbox", IA_ARCHIVE),
            (mbox_data / "ia/no.ia.citations.mbox", IA_ARCHIVE),
            (mbox_data / "nb/no.id.overlap.mbox", NB_ARCHIVE),
            (mbox_data / "nb/no.nb.citations.mbox", NB_ARCHIVE),
        ],
    )

    results = compare_message_ids(connection)

    assert results["ia_refs_resolved_by_nb"] == 1
    assert results["nb_refs_resolved_by_ia"] == 1


def test_counts_ghost_references_by_who_cited_them(mbox_data, database, load_archives):
    """Ghosts are cited ids that neither archive holds a message for."""
    connection = load_archives(
        database,
        [
            (mbox_data / "ia/no.id.overlap.mbox", IA_ARCHIVE),
            (mbox_data / "ia/no.ia.citations.mbox", IA_ARCHIVE),
            (mbox_data / "nb/no.id.overlap.mbox", NB_ARCHIVE),
            (mbox_data / "nb/no.nb.citations.mbox", NB_ARCHIVE),
        ],
    )

    results = compare_message_ids(connection)

    assert results["ghost_cited_by_ia_only"] == 1
    assert results["ghost_cited_by_nb_only"] == 1
    assert results["ghost_cited_by_both"] == 1


def test_date_filtering_restricts_ia_ids_and_their_references(
    mbox_data, database, load_archives
):
    connection = load_archives(
        database, [(mbox_data / "ia/no.dated.citations.mbox", IA_ARCHIVE)]
    )

    results = compare_message_ids(connection, ia_date_span=SPAN)

    # Only the message inside the span is counted, and only what it cites
    assert results["ia_ids"] == 1
    assert results["ghost_cited_by_ia_only"] == 1


def test_date_filtering_leaves_nb_alone(mbox_data, database, load_archives):
    """The date-filtered comparison asks what IA adds over the span NB covers."""
    connection = load_archives(
        database,
        [
            (mbox_data / "ia/no.dated.citations.mbox", IA_ARCHIVE),
            (mbox_data / "nb/no.dated.ids.mbox", NB_ARCHIVE),
        ],
    )

    filtered = compare_message_ids(connection, ia_date_span=SPAN)

    # Both NB messages are kept, including the one outside the span
    assert filtered["nb_ids"] == 2


def test_repeated_message_ids_are_counted_once(mbox_data, database, load_archives):
    connection = load_archives(
        database, [(mbox_data / "nb/no.repeated.message.mbox", NB_ARCHIVE)]
    )

    results = compare_message_ids(connection)

    # Three messages, but <a@example.no> appears twice
    assert results["nb_ids"] == 2
