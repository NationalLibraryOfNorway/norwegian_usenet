"""Print the newsgroup pairs whose averaged message embeddings are most and least alike."""

import argparse
import logging
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.metrics.pairwise import cosine_similarity

from usenet_no.embed_messages import (
    ARCHIVE_CHOICES,
    archive_sources,
    load_newsgroup_centroids,
)

logger = logging.getLogger(__name__)


def centroid_pairs(
    centroids: np.ndarray, labels: list[str], message_counts: list[int]
) -> pd.DataFrame:
    """Every pair of centroids, with the cosine similarity between them."""
    similarities = cosine_similarity(centroids)
    index_a, index_b = np.triu_indices(len(labels), k=1)
    return pd.DataFrame(
        {
            "newsgroup_a": [labels[i] for i in index_a],
            "newsgroup_b": [labels[i] for i in index_b],
            "messages_a": [message_counts[i] for i in index_a],
            "messages_b": [message_counts[i] for i in index_b],
            "cosine_similarity": similarities[index_a, index_b],
        }
    )


def as_table(pairs: pd.DataFrame) -> str:
    """Lay the pairs out for printing, the similarities to four decimals."""
    pairs = pairs.copy()
    pairs["cosine_similarity"] = pairs.cosine_similarity.map("{:.4f}".format)
    return pairs.to_string(index=False)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Print the newsgroup pairs with the most and least similar centroids",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument(
        "--embeddings-directory",
        type=Path,
        default=Path("data/output/08_make_embeddings"),
        help="Base directory containing per-model embedding subdirectories",
    )
    parser.add_argument(
        "--model",
        type=str,
        default="codefuse-ai/F2LLM-v2-0.6B",
        help="Model subdirectory under --embeddings-directory",
    )
    parser.add_argument(
        "--archive",
        choices=ARCHIVE_CHOICES,
        default="nb",
        help="Average the messages of this archive (default: %(default)s)",
    )
    parser.add_argument(
        "--top-n",
        type=int,
        default=20,
        help="How many of the most and least similar pairs to print",
    )
    args = parser.parse_args()
    logging.basicConfig(level=logging.INFO)
    logger.info("Args: %s", args)

    sources = archive_sources(args.archive)
    centroids, stems, message_counts = load_newsgroup_centroids(
        args.embeddings_directory / args.model, sources
    )

    # A stem is <newsgroup>_<source>, so the source is left on the label only
    # when both archives are averaged and a newsgroup can be there twice.
    labels = [stem if len(sources) > 1 else stem.rsplit("_", 1)[0] for stem in stems]

    pairs = centroid_pairs(centroids, labels, message_counts)

    print(f"{args.embeddings_directory / args.model}, {args.archive}")
    print(f"{len(labels):,} newsgroup centroids")
    print(f"{len(pairs):,} pairs")
    print(f"\nThe {args.top_n} pairs with the most similar centroids")
    print(as_table(pairs.nlargest(args.top_n, "cosine_similarity")))
    print(f"\nThe {args.top_n} pairs with the least similar centroids")
    print(as_table(pairs.nsmallest(args.top_n, "cosine_similarity")))
