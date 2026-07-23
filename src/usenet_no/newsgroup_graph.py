"""The newsgroup overlap table read as a graph.

Newsgroups are the vertices and an edge joins two of them when enough of their
users overlap. Both thresholds are inclusive, so a pair on the boundary is kept.
"""

import logging

import networkx as nx
import pandas as pd

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
