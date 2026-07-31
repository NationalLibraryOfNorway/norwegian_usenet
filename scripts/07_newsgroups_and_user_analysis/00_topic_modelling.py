import argparse
import logging
from pathlib import Path

from bertopic import BERTopic

from usenet_no.embed_messages import load_embeddings_and_docs
from usenet_no.topic_modelling import make_run_tag

logger = logging.getLogger(__name__)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Run BERTopic topic modelling on pre-computed message embeddings"
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
        default="jinaai/jina-embeddings-v5-text-nano",
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
        "--output-directory",
        type=Path,
        default=Path("data/output/07_newsgroups_and_user_analysis/topic_modelling"),
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

    parser.add_argument(
        "--selection",
        nargs="+",
        metavar="NEWSGROUP",
        default=DEFAULT_SELECTION,
        help="Newsgroup names to include (default: %(default)s)",
    )

    args = parser.parse_args()
    logger.info("Args: %s", args)

    embeddings_dir = args.embeddings_directory / args.model

    run_tag = make_run_tag(args.nr_topics, selection=args.selection)
    output_dir = args.output_directory / args.model / run_tag
    output_dir.mkdir(parents=True, exist_ok=True)
    logger.info("Output directory: %s", output_dir)

    embeddings, _, docs = load_embeddings_and_docs(
        embeddings_dir,
        args.ia_directory,
        args.nb_directory,
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
