"""Count the messages in each newsgroup that each other newsgroup references.

Reads the database built in step 02 and writes a directed edge list: one row
per (from_newsgroup, to_newsgroup) pair, weighted by how many distinct messages
held by the second newsgroup the first one references. A message cited by five
hundred messages weighs one here, where count_references_between_newsgroups
weighs it five hundred. References to messages outside the read body of
messages point to the placeholder newsgroup `unknown`, and references within a
newsgroup are left out.

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
)
from usenet_no.database.statistics import get_date_span

logger = logging.getLogger(__name__)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Count the messages each newsgroup references in each other newsgroup"
    )
    parser.add_argument(
        "--database-file",
        type=Path,
        default=Path("data/output/02_build_database/usenet.db"),
        help="Path to the SQLite database file",
    )
    parser.add_argument(
        "--nb-output-file",
        type=Path,
        default=Path(
            "data/output/07_newsgroups_and_user_analysis/"
            "newsgroup_referenced_message_counts_nb.csv"
        ),
        help="Path to CSV output file for the NB archive",
    )
    parser.add_argument(
        "--ia-date-filtered-output-file",
        type=Path,
        default=Path(
            "data/output/07_newsgroups_and_user_analysis/"
            "newsgroup_referenced_message_counts_ia_date_filtered.csv"
        ),
        help="Path to CSV output file for IA restricted to the NB date span",
    )
    parser.add_argument(
        "--merged-output-file",
        type=Path,
        default=Path(
            "data/output/07_newsgroups_and_user_analysis/"
            "newsgroup_referenced_message_counts_nb_and_ia_date_filtered.csv"
        ),
        help="Path to CSV output file for NB and the date-filtered IA together",
    )
    parser.add_argument(
        "--overwrite",
        action="store_true",
        help="If flagged, will overwrite existing files instead of skipping",
    )

    args = parser.parse_args()
    logging.basicConfig(level=logging.INFO)
    logger.info("Args: %s", args)

    connection = connect(args.database_file)
    nb_date_span = get_date_span(connection, NB_ARCHIVE)
    logger.info("NB date span: %s to %s", *nb_date_span)

    nb: ArchiveDatespan = (NB_ARCHIVE, None)
    ia_date_filtered: ArchiveDatespan = (IA_ARCHIVE, nb_date_span)

    for name, archive_datespans, output_file in [
        ("nb", [nb], args.nb_output_file),
        (
            "ia (date filtered)",
            [ia_date_filtered],
            args.ia_date_filtered_output_file,
        ),
        (
            "nb and ia (date filtered)",
            [nb, ia_date_filtered],
            args.merged_output_file,
        ),
    ]:
        if output_file.exists() and not args.overwrite:
            logger.info(
                "Existing file found at %s; use --overwrite to regenerate",
                output_file,
            )
            continue

        edges = count_referenced_messages(connection, archive_datespans)

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
