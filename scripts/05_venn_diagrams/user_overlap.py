"""Draw the user overlap between the date filtered IA archive and NB, by hashed email."""

import argparse
import logging
from pathlib import Path

from usenet_no.database import IA_ARCHIVE, NB_ARCHIVE, connect_archives
from usenet_no.database.comparison import VennCounts, count_user_overlap
from usenet_no.database.statistics import count_messages_per_email, get_date_span
from usenet_no.venn import write_venn_and_counts

logger = logging.getLogger(__name__)


def count_top_user_overlap(connection, nb_date_span, top_n: int) -> VennCounts:
    """Compare the `top_n` busiest emails of each archive as sets."""
    top_ia = {
        email
        for email, _ in count_messages_per_email(
            connection, IA_ARCHIVE, date_span=nb_date_span
        )[:top_n]
    }
    top_nb = {
        email for email, _ in count_messages_per_email(connection, NB_ARCHIVE)[:top_n]
    }
    return VennCounts(
        nb_only=len(top_nb - top_ia),
        ia_only=len(top_ia - top_nb),
        both=len(top_nb & top_ia),
    )


def main() -> None:
    parser = argparse.ArgumentParser(
        description=__doc__,
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
        "--out-dir",
        type=Path,
        default=Path("data/output/05_venn_diagrams"),
        help="Directory for the .json counts and .png figures",
    )
    parser.add_argument(
        "--top-n",
        type=int,
        default=100,
        help="How many of the busiest users each archive contributes to the second figure",
    )
    args = parser.parse_args()
    logging.basicConfig(level=logging.INFO)
    logger.info("Args: %s", args)

    connection = connect_archives(args.ia_database_file, args.nb_database_file)
    nb_date_span = get_date_span(connection, NB_ARCHIVE)
    logger.info("NB date span: %s to %s", *nb_date_span)

    counts = count_user_overlap(connection, ia_date_span=nb_date_span)
    logger.info("User overlap: %s", counts)
    write_venn_and_counts(
        counts,
        "User email overlap",
        args.out_dir,
        "user_overlap",
    )

    top_counts = count_top_user_overlap(connection, nb_date_span, args.top_n)
    logger.info("Top %d user overlap: %s", args.top_n, top_counts)
    write_venn_and_counts(
        top_counts,
        f"Top {args.top_n} user email overlap",
        args.out_dir,
        f"top_{args.top_n}_user_overlap",
    )

    connection.close()


if __name__ == "__main__":
    main()
