import argparse
import logging
from pathlib import Path

import numpy as np
import pandas as pd
import plotly.graph_objects as go

from usenet_no.embed_messages import (
    ARCHIVE_CHOICES,
    archive_sources,
    load_embeddings_and_docs,
)
from usenet_no.plot_utils import (
    hsl_to_hex,
    with_square_legend_swatch,
    wrap_hover_text,
)
from usenet_no.topic_modelling import (
    METHODS,
    OUTLIER_TOPIC,
    REDUCING_METHODS,
    make_run_dir,
    make_topic_labels,
)

logger = logging.getLogger(__name__)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Visualize turftopic topics over pre-computed 2-dim embeddings",
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
        "--method",
        type=str,
        choices=METHODS,
        default="topeax",
        help="Select the run that was fitted with this turftopic model",
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
        "--topics-directory",
        type=Path,
        default=Path("data/output/09_topic_modelling"),
        help="Directory containing the saved topic model runs",
    )
    parser.add_argument(
        "--nr-topics",
        type=int,
        default=None,
        metavar="N",
        help="Select the run that was fitted with this --nr-topics (omit for a run without it)",
    )
    parser.add_argument(
        "--newsgroup",
        type=str,
        default="no.religion",
        metavar="NEWSGROUP",
        help="The newsgroup the run was fitted on",
    )
    parser.add_argument(
        "--archive",
        choices=ARCHIVE_CHOICES,
        default="nb",
        help="Select the run that was fitted on this archive (default: %(default)s)",
    )
    parser.add_argument(
        "--save-fig",
        action="store_true",
        help="If flagged, will also save the figure as a .png in the run directory",
    )
    parser.add_argument(
        "--no-show",
        action="store_true",
        help="If flagged, will not open the figure in a browser, which is what a "
        "run only meant to write the .png of --save-fig wants",
    )
    args = parser.parse_args()
    logger.info("Args: %s", args)

    embedding_dir = args.embeddings_directory / args.model

    run_dir = make_run_dir(
        args.topics_directory,
        args.model,
        args.newsgroup,
        args.method,
        args.archive,
        args.nr_topics,
    )
    topics_path = run_dir / "document_topics.npy"
    topic_info_path = run_dir / "topic_info.csv"
    if not topics_path.exists() or not topic_info_path.exists():
        raise SystemExit(
            f"No topic modelling run at {run_dir}. "
            "Run scripts/09_topic_modelling/01_topic_modelling.py with the same "
            "--method, --newsgroup, --archive and --nr-topics first."
        )

    # A reducing method has already placed every document in two dimensions, and
    # those are the ones it read the topics off.
    if args.method in REDUCING_METHODS:
        coordinates_path = run_dir / "reduced_embeddings.npy"
        axis_title = "t-SNE"
        regenerate_hint = (
            "Refit the run in scripts/09_topic_modelling/01_topic_modelling.py."
        )
    else:
        coordinates_path = (
            args.embeddings_directory
            / "umap_embeddings"
            / args.model
            / f"{args.newsgroup}_{args.archive}.npy"
        )
        axis_title = "UMAP"
        regenerate_hint = (
            "Regenerate it with "
            "scripts/08_make_embeddings/02_umap_reduce_embeddings.py "
            f"--selection {args.newsgroup} --archive {args.archive} --overwrite."
        )
        if not coordinates_path.exists():
            raise SystemExit(
                f"No UMAP embeddings at {coordinates_path}. "
                "Run scripts/08_make_embeddings/02_umap_reduce_embeddings.py "
                f"with --selection {args.newsgroup} --archive {args.archive} first."
            )

    logger.info("Loading coordinates from %s", coordinates_path)
    coordinates = np.load(coordinates_path)

    _, embedding_indexer, docs = load_embeddings_and_docs(
        embedding_dir,
        args.ia_directory,
        args.nb_directory,
        selection=[args.newsgroup],
        sources=archive_sources(args.archive),
    )
    logger.info("Loaded %d messages total", len(embedding_indexer))

    if len(coordinates) != len(embedding_indexer):
        raise SystemExit(
            f"{coordinates_path} has {len(coordinates)} rows but the newsgroup loaded "
            f"{len(embedding_indexer)} messages. {regenerate_hint}"
        )

    logger.info("Loading topics from %s", topics_path)
    topics = np.load(topics_path)

    if len(topics) != len(embedding_indexer):
        raise SystemExit(
            f"{topics_path} has {len(topics)} topics but the newsgroup loaded "
            f"{len(embedding_indexer)} messages. Refit the run in "
            "scripts/09_topic_modelling/01_topic_modelling.py."
        )

    topic_info = pd.read_csv(topic_info_path)
    topic_labels = make_topic_labels(topic_info)
    short_labels = make_topic_labels(topic_info, n_words=1)

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

    symbol_map = {"nb": "circle", "ia": "triangle-up"}
    point_symbols = np.array(
        [symbol_map[stem.rsplit("_", 1)[1]] for stem in embedding_indexer]
    )
    # Only a figure holding both archives tells them apart by marker shape. With
    # one archive every marker is alike, so the legend can show that shape
    # itself and the title has nothing to explain.
    shapes_differ = args.archive == "both"

    hover_texts = np.array(
        [
            f"<b>{topic_labels[t]}</b><br><i>{stem}</i><br>"
            + wrap_hover_text(body[:400])
            for t, stem, body in zip(topics, embedding_indexer, docs)
        ]
    )

    fig = go.Figure()

    # One trace per topic, so that its legend entry holds all of its messages,
    # and the shape of every marker in it says which archive that message is from.
    for t in unique_topics:
        mask = topics == t
        x, y = coordinates[mask, 0], coordinates[mask, 1]
        symbols, text = point_symbols[mask], hover_texts[mask]
        if shapes_differ:
            x, y, symbols, text = with_square_legend_swatch(x, y, symbols, text)
        fig.add_trace(
            go.Scattergl(
                x=x,
                y=y,
                mode="markers",
                marker=dict(
                    size=5,
                    color=color_map[t],
                    symbol=symbols,
                    opacity=0.5 if t == OUTLIER_TOPIC else 0.7,
                ),
                name=short_labels[t],
                text=text,
                hovertemplate="%{text}<extra></extra>",
            )
        )

    marker_key = f"color={args.method} topic"
    if shapes_differ:
        marker_key += ", shape=source"

    fig.update_layout(
        title=f"{args.newsgroup} message embeddings, {args.archive} ({marker_key})",
        xaxis_title=f"{axis_title} 1",
        yaxis_title=f"{axis_title} 2",
        width=1100,
        height=750,
        legend=dict(font=dict(size=9)),
        hoverlabel=dict(align="left"),
    )

    if args.save_fig:
        figure_path = run_dir / "topics.png"
        fig.write_image(figure_path, scale=2)
        logger.info("Saved the figure to %s", figure_path)

    if not args.no_show:
        fig.show()
