"""The newsgroup overlap and reference tables read as graphs.

Newsgroups are the vertices. In the overlap graph an edge joins two of them
when enough of their users overlap; in the reference graph a directed edge
runs from one to another when enough of the first's references reach the
second, weighted by how many of them there are. The thresholds are inclusive,
so a pair on the boundary is kept.
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

    `overlaps` is a table with the columns of database.overlap.NewsgroupOverlap.
    Every newsgroup becomes a vertex carrying its number of users; an edge joins
    a pair with a jaccard overlap of at least `jaccard_threshold` and at least
    `min_shared_users` shared users, carrying both as edge attributes.
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

    The tables are those written by 03_statistics_per_archive, where a newsgroup
    is named after its mbox file, so the .mbox suffix is dropped here. A message
    held by two of the counted archives counts once per archive.
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
    edges: pd.DataFrame, message_counts: dict[str, int], min_reference_share: float
) -> nx.DiGraph:
    """Build a directed graph of newsgroups joined by their references.

    `edges` is a table with the columns of
    database.reference_graph.ReferenceEdge. Every newsgroup becomes a vertex
    carrying its total from `message_counts`; the placeholder unknown newsgroup
    carries None. A newsgroup the counts do not cover raises, since a naming
    mismatch would otherwise quietly size its vertex wrong.

    An edge is created where the references running from one newsgroup to the
    other are at least `min_reference_share` of every reference leaving the
    first, so newsgroups of very different sizes are held to the same
    threshold. It carries the count as `references` and the share as `share`.
    The two directions between a pair are two edges, each kept or dropped on
    its own share.
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

    shared = edges.assign(
        share=edges.number_of_references / edges.references_out_of_newsgroup
    )
    joined = shared[shared.share >= min_reference_share]
    for row in joined.itertuples():
        graph.add_edge(
            row.from_newsgroup,
            row.to_newsgroup,
            references=int(row.number_of_references),
            share=float(row.share),
        )

    logger.info(
        "Built a directed graph of %d newsgroups and %d edges,"
        " %d newsgroups with no edge",
        graph.number_of_nodes(),
        graph.number_of_edges(),
        sum(1 for _node, degree in graph.degree() if degree == 0),
    )
    return graph
