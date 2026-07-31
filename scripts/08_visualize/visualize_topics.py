import argparse
import logging
from pathlib import Path

import numpy as np
import plotly.graph_objects as go
from bertopic import BERTopic
from viz import hsl_to_hex

from usenet_no.embed_messages import load_embeddings_and_docs
from usenet_no.topic_modelling import make_run_tag

logger = logging.getLogger(__name__)


def topic_label(topic: int, topic_info, n_words: int = 5) -> str:
    if topic == -1:
        return "outliers (-1)"
    words = ", ".join(topic_info.loc[topic, "Representation"][:n_words])
    return f"Topic {topic}: {words}"


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Visualize BERTopic topics over pre-computed UMAP embeddings"
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
        help="Directory containing the saved BERTopic models",
    )
    parser.add_argument(
        "--nr-topics",
        type=int,
        default=None,
        metavar="N",
        help="Select the model that was fitted with this --nr-topics (omit for the unreduced model)",
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

    run_tag = make_run_tag(args.nr_topics, selection=args.selection)
    model_path = args.topics_directory / args.model / run_tag / "bertopic_model"
    if not model_path.exists():
        raise SystemExit(
            f"No BERTopic model at {model_path}. "
            "Run scripts/07_newsgroups_and_user_analysis/topic_modelling.py with the same --selection and "
            "--nr-topics first."
        )

    logger.info("Loading UMAP embeddings from %s", umap_cache)
    umap_2d = np.load(umap_cache)

    embeddings, embedding_indexer, docs = load_embeddings_and_docs(
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

    logger.info("Loading BERTopic model from %s", model_path)
    topic_model = BERTopic.load(str(model_path))
    topics, _ = topic_model.transform(docs, embeddings)
    topics = np.array(topics)

    topic_info = topic_model.get_topic_info().set_index("Topic")
    unique_topics = sorted(set(topics))
    logger.info("Assigned %d topics", len(unique_topics))
    for t in unique_topics:
        logger.info("%s (%d messages)", topic_label(t, topic_info), (topics == t).sum())

    color_map = {
        t: "lightgrey"
        if t == -1
        else hsl_to_hex(int(i * 360 / max(1, len(unique_topics) - 1)), 70, 50)
        for i, t in enumerate(unique_topics)
    }

    hover_texts = np.array(
        [
            f"<b>{topic_label(t, topic_info)}</b><br><i>{stem.rsplit('_', 1)[0]}</i><br>"
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
                    size=4, color=color_map[t], opacity=0.5 if t == -1 else 0.7
                ),
                name=topic_label(t, topic_info, n_words=1),
                text=hover_texts[mask],
                hovertemplate="%{text}<extra></extra>",
            )
        )

    fig.update_layout(
        title="Norwegian Usenet message embeddings (color=BERTopic topic)",
        xaxis_title="UMAP 1",
        yaxis_title="UMAP 2",
        width=1100,
        height=750,
        legend=dict(font=dict(size=9)),
    )
    fig.show()
