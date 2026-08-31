from usenet_no.database import IA_ARCHIVE, NB_ARCHIVE
from usenet_no.database.reference_graph import (
    UNKNOWN_NEWSGROUP,
    ReferenceResolution,
    resolution_edges,
)

RESOLUTION = ReferenceResolution(
    total=10, resolved_in_archive=6, resolved_in_other_archive=3, unresolved=1
)


def test_the_archive_keeps_its_own_references_on_its_self_loop():
    edges = resolution_edges(NB_ARCHIVE, IA_ARCHIVE, RESOLUTION)

    assert edges[0] == (NB_ARCHIVE, NB_ARCHIVE, 6)


def test_what_only_the_other_archive_holds_runs_to_it():
    edges = resolution_edges(NB_ARCHIVE, IA_ARCHIVE, RESOLUTION)

    assert edges[1] == (NB_ARCHIVE, IA_ARCHIVE, 3)


def test_what_neither_archive_holds_runs_to_the_placeholder():
    edges = resolution_edges(NB_ARCHIVE, IA_ARCHIVE, RESOLUTION)

    assert edges[2] == (NB_ARCHIVE, UNKNOWN_NEWSGROUP, 1)


def test_the_three_edges_add_up_to_the_total():
    edges = resolution_edges(IA_ARCHIVE, NB_ARCHIVE, RESOLUTION)

    assert sum(edge.number_of_references for edge in edges) == RESOLUTION.total
    assert {edge.from_archive for edge in edges} == {IA_ARCHIVE}
