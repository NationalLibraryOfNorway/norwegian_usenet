"""The newsgroup overlap and reference tables read as graphs.

Newsgroups are the vertices. In the overlap graph an edge joins two of them
when enough of their users overlap; in the reference graph a directed edge
runs from one to another weighted by the references between them. The
thresholds are inclusive, so a pair on the boundary is kept.
"""

import logging
from pathlib import Path

import networkx as nx
import pandas as pd

from usenet_no.database.reference_graph import UNKNOWN_NEWSGROUP

logger = logging.getLogger(__name__)


def build_overlap_graph(
    overlaps: pd.DataFrame, jaccard_threshold: float, min_shared_users: int
) -> nx.Graph:
    """Build a graph of newsgroups joined by their shared users.

    `overlaps` is a table with columns the same as the fields in database.overlap.NewsgroupOverlap.
    Every newsgroup is represented as a vertex. An edge is created if the newsgroups the vertices represent
    have a jaccard overlap of least `jaccard_threshold` AND have at least `min_shared_users` shared users.

    Edges in the graph carries the pair's `jaccard` and `shared_users`,
    and vertices carry the number of users.
    """
    graph = nx.Graph()
    for newsgroup, users in [
        *zip(overlaps.newsgroup_a, overlaps.users_a),
        *zip(overlaps.newsgroup_b, overlaps.users_b),
    ]:
        graph.add_node(newsgroup, users=int(users))

    joined = overlaps[
        (overlaps.jaccard >= jaccard_threshold)
        & (overlaps.shared_users >= min_shared_users)
    ]
    for row in joined.itertuples():
        graph.add_edge(
            row.newsgroup_a,
            row.newsgroup_b,
            jaccard=float(row.jaccard),
            shared_users=int(row.shared_users),
        )

    logger.info(
        "Built a graph of %d newsgroups and %d edges, %d newsgroups with no edge",
        graph.number_of_nodes(),
        graph.number_of_edges(),
        sum(1 for _node, degree in graph.degree() if degree == 0),
    )
    return graph


def load_message_counts(count_files: list[Path]) -> dict[str, int]:
    """Total messages per newsgroup, summed over per-archive count tables.

    The tables are those written by 03_statistics_per_archive, where a
    newsgroup is named after its mbox file, so the .mbox suffix is dropped
    here. A message held by two of the counted archives counts once per
    archive holding it.
    """
    counts: dict[str, int] = {}
    for count_file in count_files:
        table = pd.read_csv(count_file)
        for newsgroup, message_count in zip(table.newsgroup, table.message_count):
            name = newsgroup.removesuffix(".mbox")
            counts[name] = counts.get(name, 0) + int(message_count)

    logger.info("Loaded message counts for %d newsgroups", len(counts))
    return counts


def build_reference_graph(
    edges: pd.DataFrame, message_counts: dict[str, int], min_references: int
) -> nx.DiGraph:
    """Build a directed graph of newsgroups joined by their references.

    `edges` is a table with columns the same as the fields in
    database.reference_graph.ReferenceEdge. Every newsgroup in the table is
    represented as a vertex, carrying its total from `message_counts`; the
    placeholder unknown newsgroup is no newsgroup and carries None. A
    newsgroup the counts do not cover raises, since a naming mismatch would
    otherwise quietly size its vertex wrong.

    An edge is created if at least `min_references` references run from the
    one newsgroup to the other, and carries that number as `references`. The
    two directions between a pair are two edges, each cleared or dropped on
    its own weight.
    """
    newsgroups = sorted(set(edges.from_newsgroup) | set(edges.to_newsgroup))
    missing = [
        newsgroup
        for newsgroup in newsgroups
        if newsgroup != UNKNOWN_NEWSGROUP and newsgroup not in message_counts
    ]
    if missing:
        raise ValueError(f"Newsgroups without a message count: {', '.join(missing)}")

    graph = nx.DiGraph()
    for newsgroup in newsgroups:
        graph.add_node(newsgroup, messages=message_counts.get(newsgroup))

    joined = edges[edges.number_of_references >= min_references]
    for row in joined.itertuples():
        graph.add_edge(
            row.from_newsgroup,
            row.to_newsgroup,
            references=int(row.number_of_references),
        )

    logger.info(
        "Built a directed graph of %d newsgroups and %d edges,"
        " %d newsgroups with no edge",
        graph.number_of_nodes(),
        graph.number_of_edges(),
        sum(1 for _node, degree in graph.degree() if degree == 0),
    )
    return graph


def select_newsgroups(graph: nx.Graph, selection: list[str]) -> nx.Graph:
    """Keep only the named newsgroups, and the edges running between them.

    A name that is not a vertex in the graph raises, since a misspelled name
    would otherwise quietly leave a newsgroup out of the picture. The
    selection keeps the kind of graph it is given, so a directed graph stays
    directed.
    """
    missing = sorted(set(selection) - set(graph.nodes))
    if missing:
        raise ValueError(f"Newsgroups not in the graph: {', '.join(missing)}")

    selected = graph.subgraph(selection).copy()
    logger.info(
        "Selected %d newsgroups, joined by %d of the %d edges",
        selected.number_of_nodes(),
        selected.number_of_edges(),
        graph.number_of_edges(),
    )
    return selected
