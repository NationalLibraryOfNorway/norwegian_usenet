"""Count the references running from each newsgroup to each other newsgroup.

Reads the database built in step 02 and writes a directed edge list: one row
per (from_newsgroup, to_newsgroup) pair. `--count references` weighs the pair by
the number of references messages in the first make to messages held by the
second, and `--count referenced-messages` by how many distinct messages of the
second are referenced at all, so a message cited by five hundred messages weighs
five hundred in the first and one in the second. References to messages outside
the read body of messages point to the placeholder newsgroup `unknown`, and
references within a newsgroup are left out.

Three bodies of messages are covered: NB, IA restricted to the NB date span,
and the two together.
"""

import argparse
import logging
from pathlib import Path

import pandas as pd

from usenet_no.database import IA_ARCHIVE, NB_ARCHIVE, connect
from usenet_no.database.overlap import ArchiveDatespan
from usenet_no.database.reference_graph import (
    ReferenceEdge,
    count_referenced_messages,
    count_references,
)
from usenet_no.database.statistics import get_date_span

logger = logging.getLogger(__name__)

COUNTS = {
    "references": ("newsgroup_reference_counts", count_references),
    "referenced-messages": (
        "newsgroup_referenced_message_counts",
        count_referenced_messages,
    ),
}


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Count the references running between pairs of newsgroups",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument(
        "--database-file",
        type=Path,
        default=Path("data/output/02_build_database/usenet.db"),
        help="Path to the SQLite database file",
    )
    parser.add_argument(
        "--count",
        type=str,
        choices=COUNTS,
        default="references",
        help="Weigh a pair by the references it carries, or by the messages referenced",
    )
    parser.add_argument(
        "--output-directory",
        type=Path,
        default=Path("data/output/09_newsgroups_and_user_analysis"),
        help="Directory to save the edge list of each body of messages",
    )
    parser.add_argument(
        "--overwrite",
        action="store_true",
        help="If flagged, will overwrite existing files instead of skipping",
    )

    args = parser.parse_args()
    logging.basicConfig(level=logging.INFO)
    logger.info("Args: %s", args)

    file_stem, count_edges = COUNTS[args.count]

    connection = connect(args.database_file)
    nb_date_span = get_date_span(connection, NB_ARCHIVE)
    logger.info("NB date span: %s to %s", *nb_date_span)

    nb: ArchiveDatespan = (NB_ARCHIVE, None)
    ia_date_filtered: ArchiveDatespan = (IA_ARCHIVE, nb_date_span)

    for name, archive_datespans, suffix in [
        ("nb", [nb], "nb"),
        ("ia (date filtered)", [ia_date_filtered], "ia_date_filtered"),
        (
            "nb and ia (date filtered)",
            [nb, ia_date_filtered],
            "nb_and_ia_date_filtered",
        ),
    ]:
        output_file = args.output_directory / f"{file_stem}_{suffix}.csv"

        if output_file.exists() and not args.overwrite:
            logger.info(
                "Existing file found at %s; use --overwrite to regenerate",
                output_file,
            )
            continue

        edges = count_edges(connection, archive_datespans)

        output_file.parent.mkdir(parents=True, exist_ok=True)
        pd.DataFrame(edges, columns=ReferenceEdge._fields).to_csv(
            output_file, index=False
        )

        logger.info(
            "%s: %d directed edges between %d newsgroups. See the edge list in %s",
            name,
            len(edges),
            len({group for edge in edges for group in (edge[0], edge[1])}),
            output_file,
        )

    connection.close()
