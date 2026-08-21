"""Draw the message overlap between the date filtered IA archive and NB, by id and by body."""

import argparse
import logging
from pathlib import Path

from usenet_no.database import NB_ARCHIVE, connect_archives
from usenet_no.database.comparison import count_body_overlap, count_message_id_overlap
from usenet_no.database.statistics import get_date_span
from usenet_no.venn import write_venn_and_counts

logger = logging.getLogger(__name__)


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
    args = parser.parse_args()
    logging.basicConfig(level=logging.INFO)
    logger.info("Args: %s", args)

    connection = connect_archives(args.ia_database_file, args.nb_database_file)
    nb_date_span = get_date_span(connection, NB_ARCHIVE)
    logger.info("NB date span: %s to %s", *nb_date_span)

    id_counts = count_message_id_overlap(connection, ia_date_span=nb_date_span)
    logger.info("Message id overlap: %s", id_counts)
    write_venn_and_counts(
        id_counts,
        "Message overlap by id",
        args.out_dir,
        "message_id_overlap",
    )

    body_counts = count_body_overlap(connection, ia_date_span=nb_date_span)
    logger.info("Message body overlap: %s", body_counts)
    write_venn_and_counts(
        body_counts,
        "Message overlap by body",
        args.out_dir,
        "message_body_overlap",
    )

    connection.close()


if __name__ == "__main__":
    main()
