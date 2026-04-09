import argparse
import logging
from pathlib import Path

from sentence_transformers import SentenceTransformer

from usenet_no.embed_messages import embed_mbox_file, get_closest_n_files

logger = logging.getLogger(__name__)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Embed messages from the N newsgroups closest to K messages in size"
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
        "--n",
        type=int,
        default=10,
        metavar="N",
        help="Number of newsgroups to embed from each archive",
    )
    parser.add_argument(
        "--k",
        type=int,
        required=True,
        metavar="K",
        help="Target number of messages per newsgroup",
    )
    parser.add_argument(
        "--ia-counts-file",
        type=Path,
        default=Path("data/messages_per_group_ia.csv"),
        help="CSV file with precomputed IA mbox message counts",
    )
    parser.add_argument(
        "--nwa-counts-file",
        type=Path,
        default=Path("data/messages_per_group_nwa.csv"),
        help="CSV file with precomputed NWA mbox message counts",
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

    ia_files = get_closest_n_files(
        args.ia_directory, args.n, args.k, args.ia_counts_file
    )
    nwa_files = get_closest_n_files(
        args.nwa_directory, args.n, args.k, args.nwa_counts_file
    )

    logger.info("Loading model %s", args.model)
    model = SentenceTransformer(args.model)
    model.max_seq_length = args.max_seq_length

    for mbox_file in ia_files:
        embed_mbox_file(
            mbox_file, "ia", model, model_output_dir, args.overwrite, args.batch_size
        )

    for mbox_file in nwa_files:
        embed_mbox_file(
            mbox_file, "nwa", model, model_output_dir, args.overwrite, args.batch_size
        )
