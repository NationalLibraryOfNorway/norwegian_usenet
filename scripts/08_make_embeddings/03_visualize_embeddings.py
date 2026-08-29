import argparse
import logging
from pathlib import Path

import numpy as np
import plotly.graph_objects as go

from usenet_no.embed_messages import (
    ARCHIVE_CHOICES,
    REDUCTION_AXIS_TITLES,
    REDUCTION_CHOICES,
    archive_sources,
    load_embeddings_and_docs,
    reduction_cache_path,
)
from usenet_no.plot_utils import (
    hsl_to_hex,
    with_square_legend_swatch,
    wrap_hover_text,
)

logger = logging.getLogger(__name__)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Visualize pre-computed 2-dimensional message embeddings "
        "with Plotly",
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
        help="Plot the messages of this archive (default: %(default)s)",
    )
    parser.add_argument(
        "--reduction",
        choices=REDUCTION_CHOICES,
        default="umap",
        help="Plot the embeddings 02 reduced with this algorithm "
        "(default: %(default)s)",
    )
    parser.add_argument(
        "--flatten-legend",
        action="store_true",
        help="Give every newsgroup one legend entry covering every archive plotted, "
        "instead of one per newsgroup and archive. A figure of one archive holds "
        "one entry per newsgroup either way",
    )
    parser.add_argument(
        "--plot-centroids",
        action="store_true",
        help="If flagged, will also plot the mean position of the messages of each "
        "newsgroup, as a marker with a black outline and a black label",
    )
    parser.add_argument(
        "--save-fig",
        action="store_true",
        help="If flagged, will also save the figure as a .png next to the cache "
        "it is plotted from, holding the scatter alone and none of the message "
        "texts the interactive figure shows on hover",
    )
    args = parser.parse_args()
    logger.info(args)

    embedding_dir = args.embeddings_directory / args.model

    sources = archive_sources(args.archive)

    cache_path = reduction_cache_path(
        args.embeddings_directory,
        args.model,
        args.selection,
        args.archive,
        args.reduction,
    )

    logger.info("Loading %s embeddings from %s", args.reduction, cache_path)
    embeddings_2d = np.load(cache_path)

    _, embedding_indexer, text_indexer = load_embeddings_and_docs(
        embedding_dir,
        args.ia_directory,
        args.nb_directory,
        selection=args.selection,
        sources=sources,
    )
    logger.info("Loaded %d messages total", len(embedding_indexer))

    if len(embeddings_2d) != len(embedding_indexer):
        raise SystemExit(
            f"{cache_path} has {len(embeddings_2d)} rows but the selection loaded "
            f"{len(embedding_indexer)} messages. Regenerate it with "
            "scripts/08_make_embeddings/02_reduce_embeddings.py "
            f"--archive {args.archive} --reduction {args.reduction} --overwrite."
        )

    newsgroups_indexer = np.array([s.rsplit("_", 1)[0] for s in embedding_indexer])
    sources_indexer = np.array([s.rsplit("_", 1)[1] for s in embedding_indexer])

    symbol_map = {"nb": "circle", "ia": "triangle-up"}
    point_symbols = np.array([symbol_map[source] for source in sources_indexer])
    # Only a figure holding both archives tells them apart by marker shape. With
    # one archive every marker is alike, so the legend can show that shape
    # itself and the title has nothing to explain.
    shapes_differ = args.archive == "both"
    unique_newsgroups = sorted(set(newsgroups_indexer.tolist()))
    color_map = {
        ng: hsl_to_hex(int(i * 360 / len(unique_newsgroups)), 70, 50)
        for i, ng in enumerate(unique_newsgroups)
    }

    hover_texts = np.array(
        [
            f"<b>{stem}</b><br>" + wrap_hover_text(body[:400])
            for stem, body in zip(embedding_indexer, text_indexer)
        ]
    )

    # A flattened legend holds every newsgroup once, and the shape of each marker
    # in its trace is what says which archive that message is from. One archive
    # has nothing to tell apart, so its legend is flat whatever the flag says.
    if args.flatten_legend or not shapes_differ:
        traces = [(ng, ng, newsgroups_indexer == ng) for ng in unique_newsgroups]
    else:
        traces = [
            (
                f"{ng} ({source})",
                ng,
                (newsgroups_indexer == ng) & (sources_indexer == source),
            )
            for ng in unique_newsgroups
            for source in sources
        ]

    fig = go.Figure()

    for name, newsgroup, mask in traces:
        if not mask.any():
            continue
        x, y = embeddings_2d[mask, 0], embeddings_2d[mask, 1]
        symbols, text = point_symbols[mask], hover_texts[mask]
        # An unflattened trace holds one archive, so its swatch already says
        # which, and so does every trace when only one archive is plotted.
        if args.flatten_legend and shapes_differ:
            x, y, symbols, text = with_square_legend_swatch(x, y, symbols, text)
        fig.add_trace(
            go.Scattergl(
                x=x,
                y=y,
                mode="markers",
                marker={
                    "size": 6,
                    "color": color_map[newsgroup],
                    "symbol": symbols,
                    "opacity": 0.7,
                },
                name=name,
                text=text,
                hovertemplate="%{text}<extra></extra>",
            )
        )

    # One centroid per newsgroup, averaged over every message plotted of it, so a
    # figure of both archives holds one marker rather than one per archive. They
    # go in a trace of their own, kept out of the legend the newsgroup colours
    # already cover, and drawn with Scattergl like the messages, since a trace of
    # another kind lands on a layer of its own rather than over them.
    if args.plot_centroids:
        centroids = np.array(
            [
                embeddings_2d[newsgroups_indexer == ng].mean(axis=0)
                for ng in unique_newsgroups
            ]
        )
        fig.add_trace(
            go.Scattergl(
                x=centroids[:, 0],
                y=centroids[:, 1],
                mode="markers+text",
                marker={
                    "size": 8,
                    "color": [color_map[ng] for ng in unique_newsgroups],
                    "line": {"width": 1.5, "color": "black"},
                },
                text=unique_newsgroups,
                textposition="top center",
                textfont={"size": 13, "color": "black"},
                showlegend=False,
                hovertemplate="<b>%{text}</b> centroid<extra></extra>",
            )
        )

    marker_key = "color=newsgroup"
    if shapes_differ:
        marker_key += ", shape=source"

    axis_title = REDUCTION_AXIS_TITLES[args.reduction]

    # Naming the archive is worth the room only where the figure holds more
    # than one of them.
    archive_key = f", {args.archive}" if shapes_differ else ""

    fig.update_layout(
        title=f"Norwegian Usenet message embeddings{archive_key} ({marker_key})",
        xaxis_title=f"{axis_title} 1",
        yaxis_title=f"{axis_title} 2",
        width=1000,
        height=700,
        legend={"font": {"size": 9}},
        hoverlabel={"align": "left"},
    )

    if args.save_fig:
        figure_path = cache_path.with_suffix(".png")
        static_fig = go.Figure(fig)
        # The centroid labels are drawn on the figure itself, so only the message
        # traces lose the text they carry for their hover labels alone.
        static_fig.update_traces(
            text=None,
            hovertemplate=None,
            hoverinfo="skip",
            selector={"mode": "markers"},
        )
        static_fig.write_image(figure_path, scale=2)
        logger.info("Saved the figure to %s", figure_path)

    fig.show()
