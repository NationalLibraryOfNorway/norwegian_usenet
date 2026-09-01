"""Draw the user overlap between the date filtered IA archive and NB, by hashed email.

Needs both user databases: the email ids of the two archives are unrelated, so
the hashed address is the only thing that says a user of one is a user of the
other. Nothing read here is written out; the figures and counts are of users, not
users themselves.
"""

import argparse
import logging
from pathlib import Path

from usenet_no.database import IA_ARCHIVE, NB_ARCHIVE, connect_archives_and_users
from usenet_no.database.comparison import VennCounts, count_user_overlap
from usenet_no.database.statistics import count_messages_per_email_hash, get_date_span
from usenet_no.venn import write_venn_and_counts

logger = logging.getLogger(__name__)


def count_top_user_overlap(connection, nb_date_span, top_n: int) -> VennCounts:
    """Compare the `top_n` busiest emails of each archive as sets."""
    top_ia = {
        email
        for email, _ in count_messages_per_email_hash(
            connection, IA_ARCHIVE, date_span=nb_date_span
        )[:top_n]
    }
    top_nb = {
        email
        for email, _ in count_messages_per_email_hash(connection, NB_ARCHIVE)[:top_n]
    }
    return VennCounts(
        nb_only=len(top_nb - top_ia),
        ia_only=len(top_ia - top_nb),
        both=len(top_nb & top_ia),
    )


def print_busiest_shared_users(connection, nb_date_span, top_n: int) -> None:
    """Print the users both archives hold that posted most, as a share of each archive."""
    ia_counts = dict(
        count_messages_per_email_hash(connection, IA_ARCHIVE, date_span=nb_date_span)
    )
    nb_counts = dict(count_messages_per_email_hash(connection, NB_ARCHIVE))
    total_ia = sum(ia_counts.values())
    total_nb = sum(nb_counts.values())

    shared = sorted(
        (email for email in ia_counts if email in nb_counts),
        key=lambda email: (-ia_counts[email], email),
    )
    print(f"\nThe busiest of the {len(shared):,} users both archives hold")
    print(f"{'hashed email':<20} {'of IA':>8} {'of NB':>8}")
    for email in shared[:top_n]:
        ia_share = ia_counts[email] / total_ia * 100
        nb_share = nb_counts[email] / total_nb * 100
        print(f"{email:<20} {ia_share:>7.2f}% {nb_share:>7.2f}%")


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
    parser.add_argument(
        "--top-n",
        type=int,
        default=100,
        help="How many of the busiest users each archive contributes to the second figure",
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

    print_busiest_shared_users(connection, nb_date_span, top_n=10)

    connection.close()


if __name__ == "__main__":
    main()
