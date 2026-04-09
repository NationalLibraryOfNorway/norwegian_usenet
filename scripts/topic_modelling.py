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

        mbox_file = source_dirs[source] / f"{mbox_stem}.mbox"
        if not mbox_file.exists():
            logger.warning("mbox file not found: %s, skipping", mbox_file)
            continue

        embeddings = np.load(emb_file)

        if min_messages is not None and len(embeddings) < min_messages:
            continue
        if max_messages is not None and len(embeddings) > max_messages:
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
    parser.add_argument(
        "--min-messages",
        type=int,
        default=None,
        metavar="N",
        help="Only include newsgroups with at least N messages",
    )
    parser.add_argument(
        "--max-messages",
        type=int,
        default=None,
        metavar="N",
        help="Only include newsgroups with at most N messages",
    )

    args = parser.parse_args()
    logger.info("Args: %s", args)

    embeddings_dir = args.embeddings_directory / args.model
    output_dir = args.output_directory / args.model
    output_dir.mkdir(parents=True, exist_ok=True)

    embeddings, docs = load_embeddings_and_docs(
        embeddings_dir,
        args.ia_directory,
        args.nwa_directory,
        args.min_messages,
        args.max_messages,
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
