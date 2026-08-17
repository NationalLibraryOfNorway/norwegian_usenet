"""Count the references made in the NB archive, split by where they resolve.

Reads the database built in step 02 and writes a .json file of four counts. A
reference is a (referring message, referenced id) pair with the newsgroup left
out, counted once however many newsgroups or archives hold either end of it: the
total, the ones pointing at a message NB holds, the ones NB has lost but IA
still holds, and the ones neither archive holds. The three groups add up to the
total. Messages with no message id of their own are left out. Both archives are
read whole, without a date filter.
"""

import argparse
import json
import logging
from pathlib import Path

from usenet_no.database import IA_ARCHIVE, NB_ARCHIVE, connect
from usenet_no.database.reference_graph import count_reference_resolution

logger = logging.getLogger(__name__)


def main() -> None:
    parser = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument(
        "--database-file",
        type=Path,
        default=Path("data/output/02_build_database/usenet.db"),
        help="Path to the SQLite database file",
    )
    parser.add_argument(
        "--output-file",
        type=Path,
        default=Path(
            "data/output/06_graphs_and_references/nb_archive_reference_count.json"
        ),
        help="The .json file to write the counts to",
    )
    args = parser.parse_args()
    logging.basicConfig(level=logging.INFO)
    logger.info("Args: %s", args)

    connection = connect(args.database_file)
    resolution = count_reference_resolution(
        connection, (NB_ARCHIVE, None), (IA_ARCHIVE, None)
    )
    connection.close()

    counts = {
        "total_references": resolution.total,
        "resolved_in_nb": resolution.resolved_in_archive,
        "resolved_in_ia_only": resolution.resolved_in_other_archive,
        "unresolved": resolution.unresolved,
    }

    args.output_file.parent.mkdir(parents=True, exist_ok=True)
    args.output_file.write_text(json.dumps(counts, indent=2))
    logger.info("Wrote counts to %s", args.output_file)


if __name__ == "__main__":
    main()
