import argparse
import json
import logging
import sys
from dataclasses import asdict
from pathlib import Path

from usenet_no.replacement_char_recovery import (
    build_norwegian_vocabulary_index,
    compute_recovery_statistics,
    count_replacement_words,
    iter_message_bodies,
)

logger = logging.getLogger(__name__)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Count how many U+FFFD (�) words in the IA archive can be"
        " unambiguously resolved to a word in the NB archive vocabulary, by"
        " masking æ/ø/å/Æ/Ø/Å to U+FFFD and matching on the shared key. Only"
        " aggregate counts are written; the words themselves are not."
    )
    parser.add_argument(
        "--ia-directory",
        type=Path,
        default=Path("data/input/internet_archive/date_filtered"),
        help="Directory containing Internet Archive (IA) .mbox files",
    )
    parser.add_argument(
        "--nb-directory",
        type=Path,
        default=Path("data/input/nb/utf_8_data"),
        help="Directory containing Nasjonalbiblioteket (NB) .mbox files",
    )
    parser.add_argument(
        "--output-file",
        type=Path,
        default=Path("data/output/04_compare_archives/replacement_char_recovery.json"),
        help="Path to JSON output file",
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

    logger.info(
        "Building NB Norwegian-word vocabulary index from %s", args.nb_directory
    )
    vocabulary_index = build_norwegian_vocabulary_index(
        iter_message_bodies(args.nb_directory)
    )

    logger.info("Counting IA replacement-character words from %s", args.ia_directory)
    ia_word_counts = count_replacement_words(iter_message_bodies(args.ia_directory))

    statistics = compute_recovery_statistics(vocabulary_index, ia_word_counts)

    args.output_file.parent.mkdir(parents=True, exist_ok=True)
    with args.output_file.open(mode="w", encoding="utf-8") as file:
        json.dump(asdict(statistics), file, ensure_ascii=False, indent=2)

    logger.info("Wrote statistics to %s", args.output_file)
    logger.info("Statistics: %s", asdict(statistics))
