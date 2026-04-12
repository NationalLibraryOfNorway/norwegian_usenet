import argparse
import logging
from pathlib import Path

from bertopic import BERTopic

from usenet_no.mbox_utils import get_message_body, message_factory, mailbox
from tqdm import tqdm
import numpy as np


logger = logging.getLogger(__name__)


def load_embeddings_and_docs(
    embeddings_dir: Path,
    ia_directory: Path,
    nwa_directory: Path,
    min_messages: int | None = None,
    max_messages: int | None = None,
    selection: list[str] | None = None,
) -> tuple[np.ndarray, list[str]]:
    source_dirs = {"ia": ia_directory, "nwa": nwa_directory}

    embedding_files = sorted(
        f for f in embeddings_dir.glob("*.npy") if not f.stem.endswith("_index")
    )

    all_embeddings = []
    all_docs = []

    for emb_file in tqdm(embedding_files, desc="Loading embeddings and documents"):
        mbox_stem, source = emb_file.stem.rsplit("_", 1)

        if source not in source_dirs:
            logger.warning("Unknown source '%s' in %s, skipping", source, emb_file.name)
            continue

        if selection is not None:
            if mbox_stem not in selection:
                continue
            embeddings = np.load(emb_file)
        else:
            embeddings = np.load(emb_file)
            if min_messages is not None and len(embeddings) < min_messages:
                continue
            if max_messages is not None and len(embeddings) > max_messages:
                continue

        mbox_file = source_dirs[source] / f"{mbox_stem}.mbox"
        if not mbox_file.exists():
            logger.warning("mbox file not found: %s, skipping", mbox_file)
            continue

        index_file = embeddings_dir / f"{emb_file.stem}_index.npy"
        indices = np.load(index_file) if index_file.exists() else None

        messages = list(mailbox.mbox(str(mbox_file), factory=message_factory))
        docs = (
            [get_message_body(messages[i]) for i in indices]
            if indices is not None
            else [get_message_body(m) for m in messages]
        )

        if len(docs) != len(embeddings):
            logger.warning(
                "Document count (%d) != embedding count (%d) for %s, skipping",
                len(docs),
                len(embeddings),
                emb_file.name,
            )
            continue

        all_embeddings.append(embeddings)
        all_docs.extend(docs)
        logger.info("Loaded %d documents from %s", len(docs), emb_file.name)

    return np.vstack(all_embeddings), all_docs


def make_run_tag(
    nr_topics: int | None,
    min_messages: int | None = None,
    max_messages: int | None = None,
    selection: list[str] | None = None,
) -> str:
    if selection is not None:
        parts = ["_".join(sorted(selection))]
    else:
        parts = []
        if min_messages is not None:
            parts.append(f"min{min_messages}")
        if max_messages is not None:
            parts.append(f"max{max_messages}")
    if nr_topics is not None:
        parts.append(f"nr{nr_topics}")
    return "_".join(parts) if parts else "default"


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Run BERTopic topic modelling on pre-computed message embeddings"
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
        "--nwa-directory",
        type=Path,
        default=Path("data/nwa_90s/utf_8_data"),
        help="Directory containing NWA mbox files",
    )
    parser.add_argument(
        "--output-directory",
        type=Path,
        default=Path("data/topics"),
        help="Directory to save the BERTopic model and topic info",
    )
    parser.add_argument(
        "--nr-topics",
        type=int,
        default=None,
        metavar="N",
        help="Reduce topics to this many after fitting (omit to keep all)",
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
        help="Only include newsgroups with at least N messages. Switches to count-based filtering.",
    )
    parser.add_argument(
        "--max-messages",
        type=int,
        default=None,
        metavar="N",
        help="Only include newsgroups with at most N messages (only used with --min-messages; no upper limit if omitted)",
    )

    args = parser.parse_args()
    logger.info("Args: %s", args)

    if args.min_messages is not None:
        args.selection = None

    embeddings_dir = args.embeddings_directory / args.model

    run_tag = make_run_tag(
        args.nr_topics,
        min_messages=args.min_messages,
        max_messages=args.max_messages,
        selection=args.selection,
    )
    output_dir = args.output_directory / args.model / run_tag
    output_dir.mkdir(parents=True, exist_ok=True)
    logger.info("Output directory: %s", output_dir)

    embeddings, docs = load_embeddings_and_docs(
        embeddings_dir,
        args.ia_directory,
        args.nwa_directory,
        min_messages=args.min_messages,
        max_messages=args.max_messages,
        selection=args.selection,
    )
    logger.info(
        "Loaded %d documents with embeddings of shape %s", len(docs), embeddings.shape
    )

    topic_model = BERTopic(nr_topics=args.nr_topics, calculate_probabilities=False)
    topics, _ = topic_model.fit_transform(docs, embeddings)
    logger.info(
        "Found %d topics", len(topic_model.get_topic_info()) - 1
    )  # -1 for outlier topic

    model_path = output_dir / "bertopic_model"
    topic_model.save(str(model_path))
    logger.info("Saved BERTopic model to %s", model_path)

    topic_info_path = output_dir / "topic_info.csv"
    topic_model.get_topic_info().to_csv(topic_info_path, index=False)
    logger.info("Saved topic info to %s", topic_info_path)
