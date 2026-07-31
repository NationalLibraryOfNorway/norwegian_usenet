import argparse
import logging
import sys
from pathlib import Path

from usenet_no.database import connect
from usenet_no.database.replacement_chars import load_replacement_char_pairs
from usenet_no.replacement_chars.robustness import (
    deduplicate_pairs,
    sample_pairs,
    write_pairs,
)

logger = logging.getLogger(__name__)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Build the evaluation set for the U+FFFD robustness check:"
        " pairs of message bodies held by both archives, where the IA copy"
        " contains the replacement character (�) and the two bodies are equal"
        " once æ/ø/å/Æ/Ø/Å and � are replaced. A crossposted message is kept"
        " once, under the smallest of the newsgroups holding it, and a sample"
        " is spread evenly over the newsgroups. The bodies are message text, so"
        " the output file is not shared.",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument(
        "--database-file",
        type=Path,
        default=Path("data/output/02_build_database/usenet.db"),
        help="Path to the SQLite database file",
    )
    parser.add_argument(
        "--ia-directory",
        type=Path,
        default=Path("data/input/internet_archive/utf_8_data"),
        help="Directory containing Internet Archive (IA) .mbox files. Must be the"
        " directory the database was built from, since messages are looked up by"
        " their position in the file",
    )
    parser.add_argument(
        "--nb-directory",
        type=Path,
        default=Path("data/input/nb/utf_8_data"),
        help="Directory containing Nasjonalbiblioteket (NB) .mbox files. Must be"
        " the directory the database was built from",
    )
    parser.add_argument(
        "--output-file",
        type=Path,
        default=Path(
            "data/output/05_evaluate_embedding_model_robustness/replacement_char_eval_pairs.jsonl"
        ),
        help="Path to JSONL output file",
    )
    parser.add_argument(
        "--max-pairs",
        type=int,
        default=5000,
        metavar="N",
        help="Write at most N pairs, spread as evenly over the newsgroups as"
        " possible, or every pair when 0 (default: %(default)s)",
    )
    parser.add_argument(
        "--random-seed",
        type=int,
        default=42,
        help="Seed for the sampling (default: %(default)s)",
    )
    parser.add_argument(
        "--overwrite",
        action="store_true",
        help="If flagged, will overwrite an existing output file instead of skipping",
    )

    args = parser.parse_args()
    logging.basicConfig(level=logging.INFO)
    logger.info("Args: %s", args)

    if args.output_file.exists() and not args.overwrite:
        logger.info(
            "Output file already exists: %s. Use --overwrite to regenerate.",
            args.output_file,
        )
        sys.exit(0)

    connection = connect(args.database_file)
    pairs = list(
        load_replacement_char_pairs(connection, args.ia_directory, args.nb_directory)
    )
    connection.close()
    logger.info("Found %d pairs differing only in the replacement char", len(pairs))

    pairs = deduplicate_pairs(pairs)
    logger.info(
        "%d pairs left after keeping one newsgroup per crossposted message", len(pairs)
    )

    sampled = sample_pairs(pairs, args.max_pairs, args.random_seed)
    if len(sampled) < len(pairs):
        logger.info(
            "Sampled %d of them over %d newsgroups with seed %d",
            len(sampled),
            len({pair.newsgroup for pair in sampled}),
            args.random_seed,
        )

    args.output_file.parent.mkdir(parents=True, exist_ok=True)
    write_pairs(sampled, args.output_file)
    logger.info("Wrote %d pairs to %s", len(sampled), args.output_file)
