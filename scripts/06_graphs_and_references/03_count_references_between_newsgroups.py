"""Count the references running from each newsgroup to each other newsgroup.

Reads the NB database built in step 02 and writes directed edge lists: one row
per (from_newsgroup, to_newsgroup) pair, weighted two ways:

newsgroup_reference_counts weigh a newgroup pair by the number of references
messages in the from_newsgroup make to messages in to_newsgroup.

newsgroup_referenced_message_counts weight a newsgroup pair by how many distinct messages
in to_newsgroup are referenced.

So a message in to_newsgroup that is referenced by hundred messages in from_newsgroup, will count as
100 in newsgroup_reference_counts, and 1 in newsgroup_referenced_message_counts.

References to messages the NB archive does not hold point to the placeholder
newsgroup `unknown`, whether or not the IA archive holds them. References
within a newsgroup are left out.

Each row also carries the from_newsgroup's own total under the same weighting:
references_from_newsgroup over every reference its messages make, the ones
within the newsgroup included, and references_out_of_newsgroup over those
reaching another newsgroup or `unknown`.
"""

import argparse
import logging
from pathlib import Path

import pandas as pd

from usenet_no.database import NB_ARCHIVE, connect_archive
from usenet_no.database.reference_graph import (
    ReferenceEdge,
    count_referenced_messages,
    count_references,
)

logger = logging.getLogger(__name__)

COUNTS = {
    "newsgroup_reference_counts": count_references,
    "newsgroup_referenced_message_counts": count_referenced_messages,
}


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Count the references running between pairs of newsgroups",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument(
        "--nb-database-file",
        type=Path,
        default=Path("data/output/02_build_database/nb.db"),
        help="Path to the SQLite database file of the NB archive",
    )
    parser.add_argument(
        "--output-directory",
        type=Path,
        default=Path("data/output/06_graphs_and_references"),
        help="Directory to save the edge lists",
    )
    parser.add_argument(
        "--overwrite",
        action="store_true",
        help="If flagged, will overwrite existing files instead of skipping",
    )

    args = parser.parse_args()
    logging.basicConfig(level=logging.INFO)
    logger.info("Args: %s", args)

    connection = connect_archive(args.nb_database_file, NB_ARCHIVE)

    for file_stem, count_edges in COUNTS.items():
        output_file = args.output_directory / f"{file_stem}_{NB_ARCHIVE}.csv"

        if output_file.exists() and not args.overwrite:
            logger.info(
                "Existing file found at %s; use --overwrite to regenerate",
                output_file,
            )
            continue

        edges = count_edges(connection, [(NB_ARCHIVE, None)])

        output_file.parent.mkdir(parents=True, exist_ok=True)
        pd.DataFrame(edges, columns=ReferenceEdge._fields).to_csv(
            output_file, index=False
        )

        logger.info(
            "%d directed edges between %d newsgroups. See the edge list in %s",
            len(edges),
            len({group for edge in edges for group in (edge[0], edge[1])}),
            output_file,
        )

    connection.close()
