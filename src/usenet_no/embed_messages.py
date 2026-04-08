import argparse
import logging
import mailbox
from collections import Counter
from pathlib import Path

import numpy as np
from sentence_transformers import SentenceTransformer
from tqdm import tqdm

from usenet_no.mbox_utils import message_factory, get_message_body

logger = logging.getLogger(__name__)


def get_top_n_files(directory: Path, n: int) -> list[Path]:
    mbox_files = list(directory.glob("*.mbox"))
    counts = Counter(
        {
            f: len(mailbox.mbox(str(f)))
            for f in tqdm(mbox_files, desc=f"Counting messages in {directory}")
        }
    )
    return [f for f, _ in counts.most_common(n)]


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
            logger.debug("Skipping empty message %d in %s", i, mbox_file.name)
            continue
        bodies.append(body)
        indices.append(i)

    if not bodies:
        logger.warning("No non-empty messages in %s, skipping", mbox_file.name)
        return

    logger.info("Embedding %d messages from %s", len(bodies), mbox_file.name)
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


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Embed messages from the top N newsgroups in IA and NWA archives"
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
        default=Path("data/embeddings"),
        help="Directory to save embedding files",
    )
    parser.add_argument(
        "--top-n",
        type=int,
        default=10,
        metavar="N",
        help="Number of largest newsgroups to embed from each archive",
    )
    parser.add_argument(
        "--model",
        type=str,
        default="codefuse-ai/F2LLM-v2-0.6B",
        help="SentenceTransformer model to use for embeddings",
    )
    parser.add_argument(
        "--batch-size",
        type=int,
        default=32,
        metavar="N",
        help="Batch size for encoding",
    )
    parser.add_argument(
        "--max-seq-length",
        type=int,
        default=512,
        metavar="N",
        help="Maximum token sequence length — messages are truncated to this length",
    )
    parser.add_argument(
        "--overwrite",
        action="store_true",
        help="Overwrite existing embedding files",
    )

    args = parser.parse_args()
    logger.info("Args: %s", args)

    model_output_dir = args.output_directory / args.model
    model_output_dir.mkdir(parents=True, exist_ok=True)

    ia_top = get_top_n_files(args.ia_directory, args.top_n)
    nwa_top = get_top_n_files(args.nwa_directory, args.top_n)

    logger.info("Loading model %s", args.model)
    model = SentenceTransformer(args.model)
    model.max_seq_length = args.max_seq_length

    for mbox_file in ia_top:
        embed_mbox_file(
            mbox_file, "ia", model, model_output_dir, args.overwrite, args.batch_size
        )

    for mbox_file in nwa_top:
        embed_mbox_file(
            mbox_file, "nwa", model, model_output_dir, args.overwrite, args.batch_size
        )
