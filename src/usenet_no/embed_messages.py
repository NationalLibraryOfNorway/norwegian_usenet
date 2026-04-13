import logging
import mailbox
from pathlib import Path

import pandas as pd

import numpy as np
from sentence_transformers import SentenceTransformer
from tqdm import tqdm

from usenet_no.mbox_utils import message_factory, get_message_body

logger = logging.getLogger(__name__)


def get_mbox_counts(
    directory: Path, counts_file: Path | None = None
) -> dict[Path, int]:
    """Get a dict wihere key is mbox file and value is number of messages in mbox file"""
    if counts_file is not None and counts_file.exists():
        logger.info("Loading mbox counts from %s", counts_file)
        df = pd.read_csv(counts_file)
        df = df[df["newsgroup"] != "Total"]
        return dict(
            zip(df["newsgroup"].map(lambda name: directory / name), df["message_count"])
        )

    mbox_files = list(directory.glob("*.mbox"))
    return {
        f: len(mailbox.mbox(str(f)))
        for f in tqdm(mbox_files, desc=f"Counting messages in {directory}")
    }


def get_top_n_files(
    directory: Path, n: int, counts_file: Path | None = None
) -> list[Path]:
    counts = get_mbox_counts(directory, counts_file)
    return sorted(counts, key=lambda f: counts[f], reverse=True)[:n]


def get_median_n_files(
    directory: Path, n: int, counts_file: Path | None = None
) -> list[Path]:
    counts = get_mbox_counts(directory, counts_file)
    sorted_files = sorted(counts, key=lambda f: counts[f])
    mid = len(sorted_files) // 2
    start = max(0, mid - n // 2)
    return sorted_files[start : start + n]


def get_closest_n_files(
    directory: Path, n: int, k: int, counts_file: Path | None = None
) -> list[Path]:
    counts = get_mbox_counts(directory, counts_file)
    return sorted(counts, key=lambda f: abs(counts[f] - k))[:n]


def embed_mbox_file(
    mbox_file: Path,
    source: str,
    model: SentenceTransformer,
    output_dir: Path,
    overwrite: bool,
    batch_size: int = 32,
) -> None:
    output_path = output_dir / f"{mbox_file.stem}_{source}.npy"
    index_path = output_dir / f"{mbox_file.stem}_{source}_index.npy"

    if output_path.exists() and not overwrite:
        logger.info("Skipping %s (already exists)", output_path.name)
        return

    mbox = mailbox.mbox(str(mbox_file), factory=message_factory)
    bodies = []
    indices = []
    total = 0
    for i, message in enumerate(mbox):
        total += 1
        body = get_message_body(message)
        if not body:
            logger.debug("Skipping empty message %d in %s", i, mbox_file)
            continue
        bodies.append(body)
        indices.append(i)

    if not bodies:
        logger.warning("No non-empty messages in %s, skipping", mbox_file)
        return

    logger.info("Embedding %d messages from %s", len(bodies), mbox_file)
    embeddings = model.encode(bodies, batch_size=batch_size, show_progress_bar=True)
    np.save(output_path, embeddings)
    logger.info("Saved embeddings to %s", output_path)

    if len(bodies) < total:
        np.save(index_path, np.array(indices))
        logger.info(
            "Saved index file to %s (%d/%d messages had content)",
            index_path,
            len(bodies),
            total,
        )
