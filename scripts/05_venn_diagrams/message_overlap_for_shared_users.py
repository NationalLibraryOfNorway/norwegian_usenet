"""Draw the message overlap between the date filtered IA archive and NB, over the users both hold.

Needs the user databases, which is where a user's email is. Dropping a user drops
the messages behind them on both sides, so a Message-ID both archives hold can
move into an archive's own region when the other archive's copy was posted by a
dropped user.
"""

import argparse
import logging
from pathlib import Path

from usenet_no.database import NB_ARCHIVE, connect_archives_and_users
from usenet_no.database.comparison import count_message_id_overlap_for_shared_users
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
        "--ia-users-database-file",
        type=Path,
        default=Path("data/output/02_build_database/ia_users.db"),
        help="Path to the SQLite user database of the IA archive",
    )
    parser.add_argument(
        "--nb-users-database-file",
        type=Path,
        default=Path("data/output/02_build_database/nb_users.db"),
        help="Path to the SQLite user database of the NB archive",
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

    connection = connect_archives_and_users(
        args.ia_database_file,
        args.nb_database_file,
        args.ia_users_database_file,
        args.nb_users_database_file,
    )
    nb_date_span = get_date_span(connection, NB_ARCHIVE)
    logger.info("NB date span: %s to %s", *nb_date_span)

    counts = count_message_id_overlap_for_shared_users(
        connection, ia_date_span=nb_date_span
    )
    logger.info("Message overlap for shared users: %s", counts)
    write_venn_and_counts(
        counts,
        "Message overlap for shared users",
        args.out_dir,
        "message_overlap_for_shared_users",
    )

    connection.close()


if __name__ == "__main__":
    main()
