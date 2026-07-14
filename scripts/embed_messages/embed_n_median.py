import argparse
import logging
from pathlib import Path

from usenet_no.embed_messages import embed_mbox_file, get_median_n_files
from sentence_transformers import SentenceTransformer

logger = logging.getLogger(__name__)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Embed messages from the N median-sized newsgroups in IA and NB archives"
    )
    parser.add_argument(
        "--ia-directory",
        type=Path,
        default=Path("data/internet_archive/utf_8_data"),
        help="Directory containing IA mbox files",
    )
    parser.add_argument(
        "--nb-directory",
        type=Path,
        default=Path("data/nb/utf_8_data"),
        help="Directory containing NB mbox files",
    )
    parser.add_argument(
        "--output-directory",
        type=Path,
        default=Path("data/embeddings"),
        help="Directory to save embedding files",
    )
    parser.add_argument(
        "--median-n",
        type=int,
        default=10,
        metavar="N",
        help="Number of median-sized newsgroups to embed from each archive",
    )
    parser.add_argument(
        "--ia-counts-file",
        type=Path,
        default=Path("data/messages_per_group_ia.csv"),
        help="CSV file with precomputed IA mbox message counts",
    )
    parser.add_argument(
        "--nb-counts-file",
        type=Path,
        default=Path("data/messages_per_group_nb.csv"),
        help="CSV file with precomputed NB mbox message counts",
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
        default=1,
        metavar="N",
        help="Batch size for encoding",
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

    ia_median = get_median_n_files(
        args.ia_directory, args.median_n, args.ia_counts_file
    )
    nb_median = get_median_n_files(
        args.nb_directory, args.median_n, args.nb_counts_file
    )

    logger.info("Loading model %s", args.model)
    model = SentenceTransformer(args.model)

    for mbox_file in ia_median:
        embed_mbox_file(
            mbox_file, "ia", model, model_output_dir, args.overwrite, args.batch_size
        )

    for mbox_file in nb_median:
        embed_mbox_file(
            mbox_file, "nb", model, model_output_dir, args.overwrite, args.batch_size
        )
