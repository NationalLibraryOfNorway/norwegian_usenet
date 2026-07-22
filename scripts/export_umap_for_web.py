"""Export UMAP embeddings to JSON for GitHub Pages visualization.

Produces compact JSON files (no message text) containing only 2D UMAP
coordinates plus newsgroup/source labels, safe to push to a public repo.
"""

import argparse
import json
import logging
from pathlib import Path

import numpy as np

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
logger = logging.getLogger(__name__)

DEFAULT_SELECTION = [
    "no.religion",
    "no.bil",
    "no.musikk",
    "no.slekt",
    "no.litteratur",
    "no.prat.politikk",
]

MODELS = [
    ("codefuse-ai/F2LLM-v2-0.6B", "umap_f2llm.json"),
    ("NbAiLab/nb-sbert-v2-large", "umap_nbsbert.json"),
]


def build_indexer(
    embedding_dir: Path,
    source_dirs: dict[str, Path],
    selection: list[str],
) -> list[str]:
    """Reconstruct the embedding indexer from .npy filenames without loading mbox files."""
    indexer = []
    for f in sorted(embedding_dir.iterdir()):
        if f.stem.endswith("_index"):
            continue
        parts = f.stem.rsplit("_", 1)
        if len(parts) != 2:
            continue
        mbox_stem, source = parts
        if mbox_stem not in selection:
            continue
        mbox_file = (
            source_dirs.get(source, Path("__nonexistent__")) / f"{mbox_stem}.mbox"
        )
        if not mbox_file.exists():
            logger.warning("mbox file not found: %s — skipping %s", mbox_file, f.name)
            continue
        embs = np.load(f)
        indexer += [f.stem] * len(embs)
        logger.info("  %s: %d entries", f.name, len(embs))
    return indexer


def export_model(
    embedding_dir: Path,
    umap_cache: Path,
    source_dirs: dict[str, Path],
    selection: list[str],
    output_path: Path,
) -> None:
    logger.info("Building indexer from %s", embedding_dir)
    indexer = build_indexer(embedding_dir, source_dirs, selection)

    logger.info("Loading UMAP cache from %s", umap_cache)
    umap_2d = np.load(umap_cache)

    if len(indexer) != len(umap_2d):
        raise ValueError(
            f"Indexer length {len(indexer)} does not match UMAP cache length "
            f"{len(umap_2d)} — re-run the UMAP computation to regenerate the cache"
        )

    newsgroups = [s.rsplit("_", 1)[0] for s in indexer]
    sources = [s.rsplit("_", 1)[1] for s in indexer]

    newsgroup_names = sorted(set(newsgroups))
    source_names = sorted(set(sources))
    ng_to_idx = {ng: i for i, ng in enumerate(newsgroup_names)}
    src_to_idx = {s: i for i, s in enumerate(source_names)}

    data = {
        "x": [round(float(v), 3) for v in umap_2d[:, 0]],
        "y": [round(float(v), 3) for v in umap_2d[:, 1]],
        "ng": [ng_to_idx[ng] for ng in newsgroups],
        "src": [src_to_idx[s] for s in sources],
        "newsgroup_names": newsgroup_names,
        "source_names": source_names,
    }

    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w") as fh:
        json.dump(data, fh, separators=(",", ":"))

    size_mb = output_path.stat().st_size / 1e6
    logger.info("Saved %d points to %s (%.1f MB)", len(indexer), output_path, size_mb)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Export UMAP embeddings to JSON for GitHub Pages (no message text)"
    )
    parser.add_argument(
        "--embeddings-directory",
        type=Path,
        default=Path("data/embeddings"),
    )
    parser.add_argument(
        "--ia-directory",
        type=Path,
        default=Path("data/internet_archive/date_filtered"),
    )
    parser.add_argument(
        "--nb-directory",
        type=Path,
        default=Path("data/nb/utf_8_data"),
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path("docs/data"),
    )
    args = parser.parse_args()

    source_dirs = {"ia": args.ia_directory, "nb": args.nb_directory}
    cache_stem = "_".join(sorted(DEFAULT_SELECTION)) + ".npy"

    for model, output_name in MODELS:
        embedding_dir = args.embeddings_directory / model
        umap_cache = args.embeddings_directory / "umap_embeddings" / model / cache_stem
        output_path = args.output_dir / output_name

        if not embedding_dir.exists():
            logger.warning(
                "Embedding directory not found: %s — skipping", embedding_dir
            )
            continue
        if not umap_cache.exists():
            logger.warning("UMAP cache not found: %s — skipping", umap_cache)
            continue

        logger.info("=== Exporting %s → %s ===", model, output_path)
        export_model(
            embedding_dir, umap_cache, source_dirs, DEFAULT_SELECTION, output_path
        )
