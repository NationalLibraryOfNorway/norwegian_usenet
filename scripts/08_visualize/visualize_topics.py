import argparse
import logging
from pathlib import Path

import numpy as np
import pandas as pd
import plotly.graph_objects as go

from usenet_no.embed_messages import load_embeddings_and_docs
from usenet_no.plot_utils import hsl_to_hex
from usenet_no.topic_modelling import (
    METHODS,
    OUTLIER_TOPIC,
    make_run_tag,
    make_topic_labels,
)

logger = logging.getLogger(__name__)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Visualize turftopic topics over pre-computed UMAP embeddings",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument(
        "--embeddings-directory",
        type=Path,
        default=Path("data/output/06_make_embeddings"),
        help="Base directory containing per-model embedding subdirectories",
    )
    parser.add_argument(
        "--model",
        type=str,
        default="codefuse-ai/F2LLM-v2-0.6B",
        help="Model subdirectory under --embeddings-directory",
    )
    parser.add_argument(
        "--method",
        type=str,
        choices=METHODS,
        default="senstopic",
        help="Select the run that was fitted with this turftopic model",
    )
    parser.add_argument(
        "--ia-directory",
        type=Path,
        default=Path("data/input/internet_archive/date_filtered"),
        help="Directory containing IA mbox files",
    )
    parser.add_argument(
        "--nb-directory",
        type=Path,
        default=Path("data/input/nb/utf_8_data"),
        help="Directory containing NB mbox files",
    )
    parser.add_argument(
        "--topics-directory",
        type=Path,
        default=Path("data/output/07_newsgroups_and_user_analysis/topic_modelling"),
        help="Directory containing the saved topic model runs",
    )
    parser.add_argument(
        "--nr-topics",
        type=int,
        default=None,
        metavar="N",
        help="Select the run that was fitted with this --nr-topics (omit for a run without it)",
    )

    DEFAULT_SELECTION = [
        "no.religion",
        "no.bil",
        "no.musikk",
        "no.slekt",
        "no.litteratur",
        "no.prat.politikk",
    ]

    parser.add_argument(
        "--selection",
        nargs="+",
        metavar="NEWSGROUP",
        default=DEFAULT_SELECTION,
        help="Newsgroup names to include (default: %(default)s)",
    )
    args = parser.parse_args()
    logger.info(args)

    embedding_dir = args.embeddings_directory / args.model

    umap_cache = (
        args.embeddings_directory
        / "umap_embeddings"
        / args.model
        / f"{'_'.join(sorted(args.selection))}.npy"
    )
    if not umap_cache.exists():
        raise SystemExit(
            f"No UMAP embeddings at {umap_cache}. "
            "Run scripts/06_make_embeddings/03_umap_reduce_embeddings.py "
            f"with --selection {' '.join(args.selection)} first."
        )

    run_tag = make_run_tag(args.method, args.nr_topics, selection=args.selection)
    run_dir = args.topics_directory / args.model / run_tag
    topics_path = run_dir / "document_topics.npy"
    topic_info_path = run_dir / "topic_info.csv"
    if not topics_path.exists() or not topic_info_path.exists():
        raise SystemExit(
            f"No topic modelling run at {run_dir}. "
            "Run scripts/07_newsgroups_and_user_analysis/topic_modelling.py with the same "
            "--method, --selection and --nr-topics first."
        )

    logger.info("Loading UMAP embeddings from %s", umap_cache)
    umap_2d = np.load(umap_cache)

    _, embedding_indexer, docs = load_embeddings_and_docs(
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
            "scripts/06_make_embeddings/03_umap_reduce_embeddings.py --overwrite."
        )

    logger.info("Loading topics from %s", topics_path)
    topics = np.load(topics_path)

    if len(topics) != len(embedding_indexer):
        raise SystemExit(
            f"{topics_path} has {len(topics)} topics but the selection loaded "
            f"{len(embedding_indexer)} messages. Refit the run in "
            "scripts/07_newsgroups_and_user_analysis/topic_modelling.py."
        )

    topic_labels = make_topic_labels(pd.read_csv(topic_info_path))
    short_labels = make_topic_labels(pd.read_csv(topic_info_path), n_words=1)

    unique_topics = sorted(set(topics.tolist()))
    logger.info("Assigned %d topics", len(unique_topics))
    for t in unique_topics:
        logger.info("%s (%d messages)", topic_labels[t], (topics == t).sum())

    color_map = {
        t: "lightgrey"
        if t == OUTLIER_TOPIC
        else hsl_to_hex(int(i * 360 / max(1, len(unique_topics) - 1)), 70, 50)
        for i, t in enumerate(unique_topics)
    }

    hover_texts = np.array(
        [
            f"<b>{topic_labels[t]}</b><br><i>{stem.rsplit('_', 1)[0]}</i><br>"
            + body[:400].replace("\n", "<br>")
            for t, stem, body in zip(topics, embedding_indexer, docs)
        ]
    )

    fig = go.Figure()

    for t in unique_topics:
        mask = topics == t
        fig.add_trace(
            go.Scattergl(
                x=umap_2d[mask, 0],
                y=umap_2d[mask, 1],
                mode="markers",
                marker=dict(
                    size=4,
                    color=color_map[t],
                    opacity=0.5 if t == OUTLIER_TOPIC else 0.7,
                ),
                name=short_labels[t],
                text=hover_texts[mask],
                hovertemplate="%{text}<extra></extra>",
            )
        )

    fig.update_layout(
        title=f"Norwegian Usenet message embeddings (color={args.method} topic)",
        xaxis_title="UMAP 1",
        yaxis_title="UMAP 2",
        width=1100,
        height=750,
        legend=dict(font=dict(size=9)),
    )
    fig.show()
