"""Count each archive's references, split by which archive resolves them.

Reads the databases built in step 02 and writes a directed edge list over three
vertices: the two archives and a placeholder `unknown` for the references
neither of them resolves. Each archive contributes three edges, which add up to
its total: a self loop for the references pointing at a message it holds
itself, an edge to the other archive for the ones it has lost but the other
still holds, and an edge to `unknown` for the rest.

A reference is a distinct (referring message id, referenced message id) pair
with the newsgroup left out, so the same reply held by several newsgroups or by
both archives counts once. Messages with no message id of their own are left
out.

Both archives are read over the NB date span, so the two rows are counted
against the same body of messages.
"""

import argparse
import logging
from pathlib import Path

import pandas as pd

from usenet_no.database import IA_ARCHIVE, NB_ARCHIVE, connect_archives
from usenet_no.database.overlap import ArchiveDatespan
from usenet_no.database.reference_graph import (
    ArchiveReferenceEdge,
    count_reference_resolution,
    resolution_edges,
)
from usenet_no.database.statistics import get_date_span

logger = logging.getLogger(__name__)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Count each archive's references by which archive resolves them",
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
        "--output-file",
        type=Path,
        default=Path(
            "data/output/06_graphs_and_references/archive_reference_counts.csv"
        ),
        help="The .csv file to write the edge list to",
    )
    parser.add_argument(
        "--overwrite",
        action="store_true",
        help="If flagged, will overwrite an existing file instead of skipping",
    )

    args = parser.parse_args()
    logging.basicConfig(level=logging.INFO)
    logger.info("Args: %s", args)

    if args.output_file.exists() and not args.overwrite:
        logger.info(
            "Existing file found at %s; use --overwrite to regenerate", args.output_file
        )
        raise SystemExit(0)

    connection = connect_archives(args.ia_database_file, args.nb_database_file)
    nb_date_span = get_date_span(connection, NB_ARCHIVE)
    logger.info("NB date span: %s to %s", *nb_date_span)

    nb: ArchiveDatespan = (NB_ARCHIVE, None)
    ia_date_filtered: ArchiveDatespan = (IA_ARCHIVE, nb_date_span)

    edges = [
        *resolution_edges(
            NB_ARCHIVE,
            IA_ARCHIVE,
            count_reference_resolution(connection, nb, ia_date_filtered),
        ),
        *resolution_edges(
            IA_ARCHIVE,
            NB_ARCHIVE,
            count_reference_resolution(connection, ia_date_filtered, nb),
        ),
    ]
    connection.close()

    args.output_file.parent.mkdir(parents=True, exist_ok=True)
    pd.DataFrame(edges, columns=ArchiveReferenceEdge._fields).to_csv(
        args.output_file, index=False
    )
    logger.info("Wrote %d edges to %s", len(edges), args.output_file)
