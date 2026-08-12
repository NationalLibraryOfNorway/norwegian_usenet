import argparse
import csv
import json
import logging
import sys
from dataclasses import asdict
from pathlib import Path

from usenet_no.database import IA_ARCHIVE, NB_ARCHIVE, connect
from usenet_no.database.core import load_id_spans, load_message_positions
from usenet_no.database.statistics import get_date_span
from usenet_no.replacement_chars.recovery import (
    RankedReplacementWord,
    build_norwegian_vocabulary_index,
    compute_recovery_statistics,
    count_replacement_words,
    iter_message_bodies,
    most_common_replacement_words,
)

logger = logging.getLogger(__name__)


def write_top_words(words: list[RankedReplacementWord], output_file: Path) -> None:
    with output_file.open(mode="w", newline="", encoding="utf-8") as file:
        writer = csv.writer(file)
        writer.writerow(["word", "occurrences", "category", "candidates"])
        writer.writerows(
            (word.word, word.occurrences, word.category, " | ".join(word.candidates))
            for word in words
        )


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Count how many U+FFFD (�) words in the IA archive can be"
        " unambiguously resolved to a word in the NB archive vocabulary, by"
        " masking æ/ø/å/Æ/Ø/Å to U+FFFD and matching on the shared key. Only"
        " aggregate counts are written; the words themselves are not.",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument(
        "--ia-directory",
        type=Path,
        default=Path("data/input/internet_archive/utf_8_data"),
        help="Directory containing Internet Archive (IA) .mbox files",
    )
    parser.add_argument(
        "--database-file",
        type=Path,
        default=Path("data/output/02_build_database/usenet.db"),
        help="Path to the SQLite database file, which says which IA messages fall in the NB date span",
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
        default=Path(
            "data/output/04_compare_message_bodies/replacement_char_recovery.json"
        ),
        help="Path to JSON output file",
    )
    parser.add_argument(
        "--top-words-file",
        type=Path,
        default=Path("data/output/04_compare_message_bodies/top_words.csv"),
        help="If set, also write the most frequent IA U+FFFD words with their"
        " NB candidates to this CSV for inspection. Contains raw words that may"
        " hold personal information, so read through before sharing it.",
    )
    parser.add_argument(
        "--top-n",
        type=int,
        default=100,
        help="How many of the most frequent words to write with --top-words-file",
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

    # The IA archive runs past the NB one at both ends, and a word can only be
    # recovered from a vocabulary the NB archive covers, so only IA messages
    # inside the NB date span are counted.
    connection = connect(args.database_file)
    nb_date_span = get_date_span(connection, NB_ARCHIVE)
    ia_positions = load_message_positions(connection, IA_ARCHIVE, nb_date_span)
    ia_message_counts = {
        newsgroup: count
        for (archive, newsgroup), (_min_id, count) in load_id_spans(connection).items()
        if archive == IA_ARCHIVE
    }
    connection.close()

    logger.info(
        "Counting IA replacement-character words from %s, within the NB date span %s to %s",
        args.ia_directory,
        *nb_date_span,
    )
    ia_word_counts = count_replacement_words(
        iter_message_bodies(args.ia_directory, ia_positions, ia_message_counts)
    )

    statistics = compute_recovery_statistics(vocabulary_index, ia_word_counts)

    args.output_file.parent.mkdir(parents=True, exist_ok=True)
    with args.output_file.open(mode="w", encoding="utf-8") as file:
        json.dump(asdict(statistics), file, ensure_ascii=False, indent=2)

    logger.info("Wrote statistics to %s", args.output_file)
    logger.info("Statistics: %s", asdict(statistics))

    if args.top_words_file is not None:
        top_words = most_common_replacement_words(
            ia_word_counts, vocabulary_index, args.top_n
        )
        args.top_words_file.parent.mkdir(parents=True, exist_ok=True)
        write_top_words(top_words, args.top_words_file)
        logger.info(
            "Wrote %d most frequent words to %s", len(top_words), args.top_words_file
        )
