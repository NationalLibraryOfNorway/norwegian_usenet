import argparse
import csv
import logging
from pathlib import Path

from usenet_no.database import connect_archives
from usenet_no.database.replacement_chars import count_replacement_char_conflicts
from usenet_no.replacement_chars import NewsgroupReplacementCharCounts

logger = logging.getLogger(__name__)


def export_replacement_char_counts_to_csv(
    counts: list[NewsgroupReplacementCharCounts], output_file: Path
) -> None:
    with output_file.open(mode="w", newline="", encoding="utf-8") as file:
        writer = csv.writer(file)
        writer.writerow(
            [
                "newsgroup",
                "message_body_conflict",
                "ia_contains_�",
                "messages_equal_with_char_replacement",
            ]
        )
        writer.writerows(
            (
                count.newsgroup,
                count.message_body_conflict,
                count.ia_contains_replacement_char,
                count.equal_with_char_replacement,
            )
            for count in counts
        )


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Count per newsgroup how many IA/NB body conflicts involve"
        " the U+FFFD replacement character in the IA copy",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
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
        help="Path to the SQLite database file of the NB archive",
    )
    parser.add_argument(
        "--ia-directory",
        type=Path,
        default=Path("data/input/internet_archive/utf_8_data"),
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
        default=Path(
            "data/output/04_compare_message_bodies/replacement_char_body_conflicts.csv"
        ),
        help="Path to CSV output file",
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
        exit(0)

    connection = connect_archives(args.ia_database_file, args.nb_database_file)
    counts = count_replacement_char_conflicts(
        connection, args.ia_directory, args.nb_directory
    )
    connection.close()

    export_replacement_char_counts_to_csv(counts, args.output_file)
    logger.info("Wrote %d rows to %s", len(counts), args.output_file)
