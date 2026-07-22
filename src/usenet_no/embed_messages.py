import logging
import mailbox
from pathlib import Path
from tqdm import tqdm

import numpy as np
from sentence_transformers import SentenceTransformer

from usenet_no.mbox_utils import message_factory, get_message_body


logger = logging.getLogger(__name__)


def embed_mbox_file(
    mbox_file: Path,
    source: str,
    model: SentenceTransformer,
    output_dir: Path,
    overwrite: bool,
    batch_size: int = 32,
    encode_kwargs: dict | None = None,
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
    embeddings = model.encode(
        bodies, batch_size=batch_size, show_progress_bar=True, **(encode_kwargs or {})
    )
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


def load_embeddings_and_docs(
    embeddings_dir: Path,
    ia_directory: Path,
    nb_directory: Path,
    selection: list[str],
) -> tuple[np.ndarray, list[str], list[str]]:
    source_dirs = {"ia": ia_directory, "nb": nb_directory}

    embedding_files = sorted(
        f for f in embeddings_dir.glob("*.npy") if not f.stem.endswith("_index")
    )

    all_embeddings = []
    all_stems = []
    all_docs = []

    for emb_file in tqdm(embedding_files, desc="Loading embeddings and documents"):
        mbox_stem, source = emb_file.stem.rsplit("_", 1)

        if source not in source_dirs:
            logger.warning("Unknown source '%s' in %s, skipping", source, emb_file.name)
            continue

        if mbox_stem not in selection:
            continue
        embeddings = np.load(emb_file)

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
        all_stems.extend([emb_file.stem] * len(embeddings))
        all_docs.extend(docs)
        logger.info("Loaded %d documents from %s", len(docs), emb_file.name)

    return np.vstack(all_embeddings), all_stems, all_docs
