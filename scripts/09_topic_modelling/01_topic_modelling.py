import argparse
import json
import logging
import sys
from pathlib import Path

import numpy as np

from usenet_no.embed_messages import (
    ARCHIVE_CHOICES,
    archive_sources,
    load_embeddings_and_docs,
)
from usenet_no.topic_modelling import (
    METHODS,
    assign_topics,
    build_topic_model,
    count_documents_per_source,
    make_run_dir,
    make_topic_words,
)

logger = logging.getLogger(__name__)

# Remove noisy info logs when fetching models from huggingface hub
logging.getLogger("httpx").setLevel(logging.WARNING)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Run turftopic topic modelling on pre-computed message embeddings",
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
        help="Model subdirectory under --embeddings-directory, also used to embed the vocabulary",
    )
    parser.add_argument(
        "--method",
        type=str,
        choices=METHODS,
        default="senstopic",
        help="Turftopic model to fit",
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
        "--output-directory",
        type=Path,
        default=Path("data/output/09_topic_modelling"),
        help="Directory to save the topic model, topic info, topic assignments and "
        "per-source topic counts",
    )
    parser.add_argument(
        "--nr-topics",
        type=int,
        default=None,
        metavar="N",
        help="Number of topics to fit (omit to let senstopic, gmm and topeax pick it, "
        "and to keep every cluster of clustering; required for s3 and keynmf)",
    )
    parser.add_argument(
        "--min-df",
        type=int,
        default=10,
        metavar="N",
        help="Drop terms from the topic descriptions that appear in fewer than N documents",
    )
    parser.add_argument(
        "--random-state",
        type=int,
        default=None,
        metavar="N",
        help="Seed to fit with (omit for an unseeded fit)",
    )

    parser.add_argument(
        "--newsgroup",
        type=str,
        default="no.religion",
        metavar="NEWSGROUP",
        help="The newsgroup to model",
    )
    parser.add_argument(
        "--archive",
        choices=ARCHIVE_CHOICES,
        default="nb",
        help="Fit on the messages of this archive (default: %(default)s)",
    )
    parser.add_argument(
        "--overwrite",
        action="store_true",
        help="If flagged, will refit a run that is already there instead of skipping",
    )

    args = parser.parse_args()
    logger.info("Args: %s", args)

    embeddings_dir = args.embeddings_directory / args.model

    output_dir = make_run_dir(
        args.output_directory,
        args.model,
        args.method,
        args.newsgroup,
        args.archive,
        args.nr_topics,
    )
    # The counts are the last file a run writes, so an interrupted one is refitted.
    source_counts_path = output_dir / "topic_source_counts.jsonl"
    if source_counts_path.exists() and not args.overwrite:
        logger.info(
            "A run already exists at %s. Use --overwrite to refit it.", output_dir
        )
        sys.exit(0)

    logger.info("Output directory: %s", output_dir)

    embeddings, embedding_indexer, docs = load_embeddings_and_docs(
        embeddings_dir,
        args.ia_directory,
        args.nb_directory,
        selection=[args.newsgroup],
        sources=archive_sources(args.archive),
    )
    logger.info(
        "Loaded %d documents with embeddings of shape %s", len(docs), embeddings.shape
    )

    topic_model = build_topic_model(
        args.method,
        args.nr_topics,
        encoder=args.model,
        min_df=args.min_df,
        random_state=args.random_state,
    )
    document_topic_matrix = topic_model.fit_transform(docs, embeddings=embeddings)
    logger.info("Found %d topics", document_topic_matrix.shape[1])

    output_dir.mkdir(parents=True, exist_ok=True)

    model_path = output_dir / "topic_model"
    topic_model.to_disk(model_path)
    logger.info("Saved %s model to %s", args.method, model_path)

    topic_info = topic_model.topics_df()
    topic_info_path = output_dir / "topic_info.csv"
    topic_info.to_csv(topic_info_path, index=False)
    logger.info("Saved topic info to %s", topic_info_path)

    topics = assign_topics(topic_model, document_topic_matrix)
    topics_path = output_dir / "document_topics.npy"
    np.save(topics_path, topics)
    logger.info("Saved one topic per document to %s", topics_path)

    reduced_embeddings = getattr(topic_model, "reduced_embeddings", None)
    if reduced_embeddings is not None and reduced_embeddings.shape[1] == 2:
        reduced_path = output_dir / "reduced_embeddings.npy"
        np.save(reduced_path, reduced_embeddings)
        logger.info(
            "Saved the two dimensions the model reduced to before clustering to %s",
            reduced_path,
        )

    sources = [stem.rsplit("_", 1)[1] for stem in embedding_indexer]
    source_counts = count_documents_per_source(
        topics, sources, make_topic_words(topic_info)
    )
    with source_counts_path.open("w", encoding="utf-8") as file:
        for row in source_counts:
            file.write(json.dumps(row, ensure_ascii=False) + "\n")
    logger.info(
        "Saved the documents per source of every topic to %s", source_counts_path
    )
