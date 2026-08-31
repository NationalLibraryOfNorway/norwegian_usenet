import argparse
import logging
from pathlib import Path

import plotly.graph_objects as go
from sklearn.decomposition import PCA

from usenet_no.embed_messages import (
    ARCHIVE_CHOICES,
    archive_sources,
    load_newsgroup_centroids,
)
from usenet_no.plot_utils import format_count

logger = logging.getLogger(__name__)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Visualize one averaged embedding per newsgroup with Plotly",
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
        "--save-fig",
        action="store_true",
        help="If flagged, will also save the figure as a .png in "
        "<embeddings-directory>/newsgroup_centroids/<model>/",
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
    sources = archive_sources(args.archive)

    centroids, stems, message_counts = load_newsgroup_centroids(embedding_dir, sources)
    logger.info(
        "Averaged %d newsgroup files of %s embeddings",
        len(stems),
        args.archive,
    )

    # One point per newsgroup is too few for UMAP or t-SNE to have neighbourhoods
    # to lay out, so the centroids are projected with PCA.
    pca = PCA(n_components=2)
    centroids_2d = pca.fit_transform(centroids)
    explained = pca.explained_variance_ratio_

    newsgroups = [stem.rsplit("_", 1)[0] for stem in stems]
    centroid_sources = [stem.rsplit("_", 1)[1] for stem in stems]

    color_map = {"nb": "#1f77b4", "ia": "#ff7f0e"}
    symbol_map = {"nb": "circle", "ia": "triangle-up"}

    fig = go.Figure()

    # One trace per archive, so the legend says which marker is which, and every
    # point carries the name of its newsgroup.
    for source in sources:
        mask = [i for i, s in enumerate(centroid_sources) if s == source]
        fig.add_trace(
            go.Scatter(
                x=centroids_2d[mask, 0],
                y=centroids_2d[mask, 1],
                mode="markers+text",
                marker={
                    "size": 10,
                    "color": color_map[source],
                    "symbol": symbol_map[source],
                },
                name=source,
                text=[newsgroups[i] for i in mask],
                textposition="top center",
                textfont={"size": 9},
                customdata=[format_count(message_counts[i]) for i in mask],
                hovertemplate="<b>%{text}</b><br>%{customdata} messages<extra></extra>",
            )
        )

    fig.update_layout(
        title=f"Norwegian Usenet newsgroup centroids, {args.archive} "
        "(color=source, one point per newsgroup)",
        xaxis_title=f"PC 1 ({explained[0]:.0%} of variance)",
        yaxis_title=f"PC 2 ({explained[1]:.0%} of variance)",
        width=1000,
        height=700,
        legend={"font": {"size": 9}},
        hoverlabel={"align": "left"},
    )

    if args.save_fig:
        figure_dir = args.embeddings_directory / "newsgroup_centroids" / args.model
        figure_dir.mkdir(parents=True, exist_ok=True)
        figure_path = figure_dir / f"centroids_{args.archive}.png"
        fig.write_image(figure_path, scale=2)
        logger.info("Saved the figure to %s", figure_path)

    if not args.no_show:
        fig.show()
