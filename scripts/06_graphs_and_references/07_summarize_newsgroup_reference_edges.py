"""Print the number of edges and references between newsgroups, and the heaviest edges."""

import argparse
import logging
from pathlib import Path

import pandas as pd

logger = logging.getLogger(__name__)

UNKNOWN_NEWSGROUP = "unknown"


def heaviest_edges(edges: pd.DataFrame, top_n: int) -> pd.DataFrame:
    """Take the `top_n` edges with the most references, with each edge's share of the references its newsgroup makes to other newsgroups."""
    references_to_newsgroups = edges.groupby(
        "from_newsgroup"
    ).number_of_references.sum()
    heaviest = edges.nlargest(top_n, "number_of_references").copy()
    heaviest["share_of_outgoing"] = (
        heaviest.number_of_references
        / heaviest.from_newsgroup.map(references_to_newsgroups)
        * 100
    ).map("{:.1f}%".format)
    return heaviest[
        ["from_newsgroup", "to_newsgroup", "number_of_references", "share_of_outgoing"]
    ]


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Print the number of edges and references between newsgroups, and the heaviest edges",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument(
        "--edge-list-file",
        type=Path,
        default=Path(
            "data/output/06_graphs_and_references/newsgroup_reference_counts_nb.csv"
        ),
        help="Path to a reference edge list CSV written by 03_count_references_between_newsgroups.py",
    )
    parser.add_argument(
        "--top-n",
        type=int,
        default=20,
        help="How many of the heaviest edges to print",
    )

    args = parser.parse_args()
    logging.basicConfig(level=logging.INFO)
    logger.info("Args: %s", args)

    edges = pd.read_csv(args.edge_list_file)
    edges = edges[edges.to_newsgroup != UNKNOWN_NEWSGROUP]

    newsgroups = set(edges.from_newsgroup) | set(edges.to_newsgroup)

    print(args.edge_list_file)
    print(f"{len(newsgroups):,} newsgroups")
    print(f"{len(edges):,} edges between newsgroups")
    print(f"{edges.number_of_references.sum():,} references between newsgroups")
    print(f"\nThe {args.top_n} heaviest edges")
    print(heaviest_edges(edges, args.top_n).to_string(index=False))
