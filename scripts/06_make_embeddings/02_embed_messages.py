import argparse
import logging
from pathlib import Path

from sentence_transformers import SentenceTransformer
from tqdm import tqdm

from usenet_no.embed_messages import embed_mbox_file

logger = logging.getLogger(__name__)

# Remove noisy info logs when fetching models from huggingface hub
logging.getLogger("httpx").setLevel(logging.WARNING)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Embed messages from selected newsgroups in IA and NB archives"
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
        default=Path("data/output/06_make_embeddings"),
        help="Directory to save embedding files",
    )
    parser.add_argument(
        "--selection",
        nargs="+",
        default=[
            "no.religion",
            "no.bil",
            "no.musikk",
            "no.slekt",
            "no.litteratur",
            "no.prat.politikk",
        ],
        help="List of newsgroups to embed",
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

    logger.info("Loading model %s", args.model)
    model = SentenceTransformer(args.model, trust_remote_code=True)

    for newsgroup in tqdm(args.selection, desc="Embedding messages in mbox files"):
        nb_mbox_file = args.nb_directory / f"{newsgroup}.mbox"
        if nb_mbox_file.exists():
            embed_mbox_file(
                nb_mbox_file,
                "nb",
                model,
                model_output_dir,
                args.overwrite,
                args.batch_size,
            )
        else:
            logger.warning("%s does not exist, can't embed messages", nb_mbox_file)

        ia_mbox_file = args.ia_directory / f"{newsgroup}.mbox"

        if ia_mbox_file.exists():
            embed_mbox_file(
                ia_mbox_file,
                "ia",
                model,
                model_output_dir,
                args.overwrite,
                args.batch_size,
            )
        else:
            logger.warning("%s does not exist, can't embed messages", ia_mbox_file)
