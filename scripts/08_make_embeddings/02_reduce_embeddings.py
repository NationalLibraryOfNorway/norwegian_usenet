import argparse
import logging
from pathlib import Path

import numpy as np
import umap
from sklearn.manifold import TSNE

from usenet_no.embed_messages import (
    ARCHIVE_CHOICES,
    REDUCTION_CHOICES,
    archive_sources,
    load_embeddings_and_docs,
    reduction_cache_path,
)

logger = logging.getLogger(__name__)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Reduce message embeddings to 2-dim vectors with UMAP or t-SNE",
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
        "--ia-directory",
        type=Path,
        default=Path("data/input/internet_archive/utf_8_data"),
        help="Directory containing IA mbox files",
    )
    parser.add_argument(
        "--nb-directory",
        type=Path,
        default=Path("data/input/nb/utf_8_data"),
        help="Directory containing NB mbox files",
    )
    parser.add_argument(
        "--selection",
        nargs="+",
        metavar="NEWSGROUP",
        default=[
            "no.religion",
            "no.bil",
            "no.musikk",
            "no.slekt",
            "no.litteratur",
            "no.prat.politikk",
        ],
        help="Newsgroup names to include (default: %(default)s)",
    )
    parser.add_argument(
        "--archive",
        choices=ARCHIVE_CHOICES,
        default="nb",
        help="Reduce the messages of this archive (default: %(default)s)",
    )
    parser.add_argument(
        "--reduction",
        choices=REDUCTION_CHOICES,
        default="tsne",
        help="Reduce with this algorithm (default: %(default)s)",
    )
    parser.add_argument(
        "--perplexity",
        type=float,
        default=50.0,
        help="Neighbourhood size t-SNE reduces against, ignored by UMAP "
        "(default: %(default)s)",
    )
    parser.add_argument(
        "--random-state", type=int, default=42, help="Random state of the reduction"
    )
    parser.add_argument(
        "--overwrite",
        action="store_true",
        help="Recompute and overwrite the cached embeddings",
    )

    args = parser.parse_args()
    logger.info("Args: %s", args)

    embedding_dir = args.embeddings_directory / args.model

    cache_path = reduction_cache_path(
        args.embeddings_directory,
        args.model,
        args.selection,
        args.archive,
        args.reduction,
    )
    cache_path.parent.mkdir(parents=True, exist_ok=True)

    if cache_path.exists() and not args.overwrite:
        logger.info(
            "Reduced embeddings already exist at %s, rerun with --overwrite to "
            "regenerate",
            cache_path,
        )
        exit(0)

    embeddings, embedding_indexer, _ = load_embeddings_and_docs(
        embedding_dir,
        args.ia_directory,
        args.nb_directory,
        selection=args.selection,
        sources=archive_sources(args.archive),
    )
    logger.info("Loaded %d messages total", len(embedding_indexer))

    logger.info(
        "Computing %s embeddings (random_state=%d)", args.reduction, args.random_state
    )
    if args.reduction == "umap":
        reducer = umap.UMAP(random_state=args.random_state)
    else:
        reducer = TSNE(
            n_components=2,
            perplexity=args.perplexity,
            init="pca",
            random_state=args.random_state,
        )
    embeddings_2d = reducer.fit_transform(embeddings)
    np.save(cache_path, embeddings_2d)
    logger.info("Saved %s embeddings to %s", args.reduction, cache_path)
