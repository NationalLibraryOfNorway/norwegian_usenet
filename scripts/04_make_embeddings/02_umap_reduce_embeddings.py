import argparse
import logging
from pathlib import Path

import numpy as np
import umap

from usenet_no.embed_messages import load_embeddings_and_docs


logger = logging.getLogger(__name__)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Reduce message embeddings to 2-dim vectors with UMAP"
    )
    parser.add_argument(
        "--embeddings-directory",
        type=Path,
        default=Path("data/embeddings"),
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
        default=Path("data/internet_archive/date_filtered"),
        help="Directory containing IA mbox files",
    )
    parser.add_argument(
        "--nb-directory",
        type=Path,
        default=Path("data/nb/utf_8_data"),
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
        "--random-state", type=int, default=42, help="UMAP random state"
    )
    parser.add_argument(
        "--overwrite",
        action="store_true",
        help="Recompute and overwrite the cached UMAP embeddings",
    )

    args = parser.parse_args()
    logger.info("Args: %s", args)

    embedding_dir = args.embeddings_directory / args.model

    umap_cache_dir = args.embeddings_directory / "umap_embeddings" / args.model
    umap_cache_dir.mkdir(parents=True, exist_ok=True)

    cache_name = "_".join(sorted(args.selection))
    umap_cache = umap_cache_dir / f"{cache_name}.npy"

    if umap_cache.exists() and not args.overwrite:
        logger.info(
            "UMAP embeddings already exist at %s, rerun with --overwrite to regenerate",
            umap_cache,
        )
        exit(0)

    embeddings, embedding_indexer, _ = load_embeddings_and_docs(
        embedding_dir,
        args.ia_directory,
        args.nb_directory,
        selection=args.selection,
    )
    logger.info("Loaded %d messages total", len(embedding_indexer))

    logger.info("Computing UMAP embeddings (random_state=%d)", args.random_state)
    umap_2d = umap.UMAP(random_state=args.random_state).fit_transform(embeddings)
    np.save(umap_cache, umap_2d)
    logger.info("Saved UMAP embeddings to %s", umap_cache)
