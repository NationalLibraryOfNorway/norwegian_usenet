import argparse
import colorsys
import logging
import mailbox
from pathlib import Path

import numpy as np
import plotly.graph_objects as go
import umap

from usenet_no.mbox_utils import message_factory, get_message_body

logger = logging.getLogger(__name__)

UMAP_RANDOM_STATE = 42


def hsl_to_hex(h, s, lightness):
    r, g, b = colorsys.hls_to_rgb(h / 360, lightness / 100, s / 100)
    return f"#{int(r * 255):02x}{int(g * 255):02x}{int(b * 255):02x}"


def load_embeddings_and_docs(
    embedding_dir: Path,
    source_dirs: dict[str, Path],
    min_messages: int | None = None,
    max_messages: int | None = None,
    selection: list[str] | None = None,
) -> tuple[np.ndarray, list[str], list[str]]:
    all_embeddings = []
    embedding_indexer = []
    text_indexer = []

    for f in sorted(embedding_dir.iterdir()):
        if f.stem.endswith("_index"):
            continue

        mbox_stem, source = f.stem.rsplit("_", 1)

        if selection is not None:
            if mbox_stem not in selection:
                continue
            embs = np.load(f)
        else:
            embs = np.load(f)
            if min_messages is not None and len(embs) < min_messages:
                continue
            if max_messages is not None and len(embs) > max_messages:
                continue

        mbox_file = source_dirs[source] / f"{mbox_stem}.mbox"
        if not mbox_file.exists():
            logger.warning("mbox file not found: %s, skipping", mbox_file)
            continue

        messages = list(mailbox.mbox(str(mbox_file), factory=message_factory))
        index_file = embedding_dir / f"{f.stem}_index.npy"
        if index_file.exists():
            indices = np.load(index_file)
            bodies = [get_message_body(messages[i]) for i in indices]
        else:
            bodies = [get_message_body(m) for m in messages]

        all_embeddings.extend(embs)
        embedding_indexer += [f.stem] * len(embs)
        text_indexer += bodies
        logger.info("Loaded %d messages from %s", len(embs), f.name)

    return np.array(all_embeddings), embedding_indexer, text_indexer


def get_umap_embeddings(
    embeddings: np.ndarray, umap_cache: Path, overwrite: bool = False
) -> np.ndarray:
    if umap_cache.exists() and not overwrite:
        logger.info("Loading UMAP embeddings from %s", umap_cache)
        return np.load(umap_cache)

    logger.info("Computing UMAP embeddings (random_state=%d)", UMAP_RANDOM_STATE)
    umap_2d = umap.UMAP(random_state=UMAP_RANDOM_STATE).fit_transform(embeddings)
    np.save(umap_cache, umap_2d)
    logger.info("Saved UMAP embeddings to %s", umap_cache)
    return umap_2d


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Visualize message embeddings with UMAP + Plotly"
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
        default=Path("data/internet_archive/utf_8_data"),
        help="Directory containing IA mbox files",
    )
    parser.add_argument(
        "--nwa-directory",
        type=Path,
        default=Path("data/nwa_90s/utf_8_data"),
        help="Directory containing NWA mbox files",
    )
    parser.add_argument(
        "--overwrite-umap-cache",
        action="store_true",
        help="Recompute and overwrite the cached UMAP embeddings",
    )

    DEFAULT_SELECTION = [
        "no.religion",
        "no.bil",
        "no.musikk",
        "no.slekt",
        "no.litteratur",
        "no.prat.politikk",
    ]

    filter_group = parser.add_mutually_exclusive_group()
    filter_group.add_argument(
        "--selection",
        nargs="+",
        metavar="NEWSGROUP",
        default=DEFAULT_SELECTION,
        help="Newsgroup names to include (default: %(default)s). Mutually exclusive with --min-messages.",
    )
    filter_group.add_argument(
        "--min-messages",
        type=int,
        default=None,
        metavar="N",
        help="Minimum number of messages for a newsgroup to be included. Switches to count-based filtering.",
    )
    parser.add_argument(
        "--max-messages",
        type=int,
        default=None,
        metavar="N",
        help="Maximum number of messages (only used with --min-messages; no upper limit if omitted)",
    )
    args = parser.parse_args()

    if args.min_messages is not None:
        args.selection = None

    embedding_dir = args.embeddings_directory / args.model
    source_dirs = {"ia": args.ia_directory, "nwa": args.nwa_directory}

    umap_cache_dir = args.embeddings_directory / "umap_embeddings" / args.model
    umap_cache_dir.mkdir(parents=True, exist_ok=True)

    if args.selection is not None:
        cache_name = "_".join(sorted(args.selection))
    else:
        min_part = (
            f"min{args.min_messages}" if args.min_messages is not None else "min0"
        )
        max_part = (
            f"max{args.max_messages}" if args.max_messages is not None else "maxinf"
        )
        cache_name = f"{min_part}_{max_part}"
    umap_cache = umap_cache_dir / f"{cache_name}.npy"

    embeddings, embedding_indexer, text_indexer = load_embeddings_and_docs(
        embedding_dir,
        source_dirs,
        min_messages=args.min_messages,
        max_messages=args.max_messages,
        selection=args.selection,
    )
    logger.info("Loaded %d messages total", len(embedding_indexer))

    umap_2d = get_umap_embeddings(embeddings, umap_cache, args.overwrite_umap_cache)

    newsgroups_indexer = [s.rsplit("_", 1)[0] for s in embedding_indexer]
    sources_indexer = [s.rsplit("_", 1)[1] for s in embedding_indexer]

    symbol_map = {"nwa": "circle", "ia": "triangle-up"}
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
