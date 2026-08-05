import argparse
import logging
from pathlib import Path

import numpy as np
import plotly.graph_objects as go

from usenet_no.embed_messages import load_embeddings_and_docs
from usenet_no.plot_utils import hsl_to_hex

logger = logging.getLogger(__name__)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Visualize pre-computed UMAP message embeddings with Plotly",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument(
        "--embeddings-directory",
        type=Path,
        default=Path("data/output/07_make_embeddings"),
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
    args = parser.parse_args()
    logger.info(args)

    embedding_dir = args.embeddings_directory / args.model

    umap_cache_dir = args.embeddings_directory / "umap_embeddings" / args.model
    cache_name = "_".join(sorted(args.selection))
    umap_cache = umap_cache_dir / f"{cache_name}.npy"

    logger.info("Loading UMAP embeddings from %s", umap_cache)
    umap_2d = np.load(umap_cache)

    _, embedding_indexer, text_indexer = load_embeddings_and_docs(
        embedding_dir,
        args.ia_directory,
        args.nb_directory,
        selection=args.selection,
    )
    logger.info("Loaded %d messages total", len(embedding_indexer))

    if len(umap_2d) != len(embedding_indexer):
        raise SystemExit(
            f"{umap_cache} has {len(umap_2d)} rows but the selection loaded "
            f"{len(embedding_indexer)} messages. Regenerate it with "
            "scripts/07_make_embeddings/02_umap_reduce_embeddings.py --overwrite."
        )

    newsgroups_indexer = [s.rsplit("_", 1)[0] for s in embedding_indexer]
    sources_indexer = [s.rsplit("_", 1)[1] for s in embedding_indexer]

    symbol_map = {"nb": "circle", "ia": "triangle-up"}
    unique_newsgroups = sorted(set(newsgroups_indexer))
    color_map = {
        ng: hsl_to_hex(int(i * 360 / len(unique_newsgroups)), 70, 50)
        for i, ng in enumerate(unique_newsgroups)
    }

    hover_texts = np.array(
        [
            f"<b>{stem}</b><br>" + body[:400].replace("\n", "<br>")
            for stem, body in zip(embedding_indexer, text_indexer)
        ]
    )

    fig = go.Figure()

    for ng in unique_newsgroups:
        for source, symbol in symbol_map.items():
            mask = np.array(
                [
                    s == source and n == ng
                    for s, n in zip(sources_indexer, newsgroups_indexer)
                ]
            )
            if not mask.any():
                continue
            fig.add_trace(
                go.Scattergl(
                    x=umap_2d[mask, 0],
                    y=umap_2d[mask, 1],
                    mode="markers",
                    marker=dict(
                        size=6, color=color_map[ng], symbol=symbol, opacity=0.7
                    ),
                    name=f"{ng} ({source})",
                    text=hover_texts[mask],
                    hovertemplate="%{text}<extra></extra>",
                )
            )

    fig.update_layout(
        title="Norwegian Usenet message embeddings (color=newsgroup, shape=source)",
        xaxis_title="UMAP 1",
        yaxis_title="UMAP 2",
        width=1000,
        height=700,
        legend=dict(font=dict(size=9)),
    )
    fig.show()
