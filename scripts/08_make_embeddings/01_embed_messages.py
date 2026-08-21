import argparse
import logging
from pathlib import Path

from sentence_transformers import SentenceTransformer
from tqdm import tqdm

from usenet_no.database import IA_ARCHIVE, NB_ARCHIVE, connect_archives
from usenet_no.database.core import load_id_spans, load_message_positions
from usenet_no.database.statistics import get_date_span
from usenet_no.embed_messages import embed_mbox_file

logger = logging.getLogger(__name__)

# Remove noisy info logs when fetching models from huggingface hub
logging.getLogger("httpx").setLevel(logging.WARNING)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Embed messages from selected newsgroups in IA and NB archives",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
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
        "--ia-database-file",
        type=Path,
        default=Path("data/output/02_build_database/ia.db"),
        help="Path to the SQLite database file of the IA archive",
    )
    parser.add_argument(
        "--nb-database-file",
        type=Path,
        default=Path("data/output/02_build_database/nb.db"),
        help="Path to the SQLite database file of the NB archive, whose date span the IA messages are filtered by",
    )
    parser.add_argument(
        "--output-directory",
        type=Path,
        default=Path("data/output/08_make_embeddings"),
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

    # The IA archive runs past the NB one at both ends, so only the messages
    # inside the NB date span are embedded. They are read from the archive's own
    # mbox files at the positions the database gives, rather than from a filtered
    # copy of those files.
    connection = connect_archives(args.ia_database_file, args.nb_database_file)
    nb_date_span = get_date_span(connection, NB_ARCHIVE)
    logger.info("NB date span: %s to %s", *nb_date_span)
    ia_positions = load_message_positions(connection, IA_ARCHIVE, nb_date_span)
    ia_message_counts = {
        newsgroup: count
        for (archive, newsgroup), (_min_id, count) in load_id_spans(connection).items()
        if archive == IA_ARCHIVE
    }
    connection.close()

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

        if not ia_mbox_file.exists():
            logger.warning("%s does not exist, can't embed messages", ia_mbox_file)
        elif newsgroup not in ia_positions:
            logger.warning("%s holds no message inside the NB date span", ia_mbox_file)
        else:
            embed_mbox_file(
                ia_mbox_file,
                "ia",
                model,
                model_output_dir,
                args.overwrite,
                args.batch_size,
                positions=ia_positions[newsgroup],
                expected_message_count=ia_message_counts[newsgroup],
            )
