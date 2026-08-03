"""Draw how many references out of one archive the other archive resolves.

A reference is *out of* an archive when it cites a Message-ID the archive does
not hold. Each figure splits those references into the ones the other archive
resolves and the ones neither of them holds.
"""

import argparse
import json
import logging
from pathlib import Path

from usenet_no.database import IA_ARCHIVE, NB_ARCHIVE, connect
from usenet_no.database.comparison import VennCounts, compare_message_ids
from usenet_no.database.statistics import get_date_span
from usenet_no.venn import write_venn

logger = logging.getLogger(__name__)

# (archive whose references are counted, archive that may resolve them)
ARCHIVE_PAIRS = ((NB_ARCHIVE, IA_ARCHIVE), (IA_ARCHIVE, NB_ARCHIVE))


def outside_references(results: dict[str, int], archive: str) -> tuple[int, int]:
    """Split one archive's outward references into (unresolved, resolved by the other)."""
    if archive == NB_ARCHIVE:
        unresolved = results["ghost_cited_by_nb_only"] + results["ghost_cited_by_both"]
        return unresolved, results["nb_refs_resolved_by_ia"]
    unresolved = results["ghost_cited_by_ia_only"] + results["ghost_cited_by_both"]
    return unresolved, results["ia_refs_resolved_by_nb"]


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
        "--out-dir",
        type=Path,
        default=Path("data/output/05_venn_diagrams"),
        help="Directory for the .json counts and .png figures",
    )
    args = parser.parse_args()
    logging.basicConfig(level=logging.INFO)
    logger.info("Args: %s", args)

    connection = connect(args.database_file)
    nb_date_span = get_date_span(connection, NB_ARCHIVE)
    logger.info("NB date span: %s to %s", *nb_date_span)

    results = compare_message_ids(connection, ia_date_span=nb_date_span)
    args.out_dir.mkdir(parents=True, exist_ok=True)

    counted = {}
    for archive, other in ARCHIVE_PAIRS:
        unresolved, resolved = outside_references(results, archive)
        total = unresolved + resolved
        logger.info(
            "%s references resolved by %s: %d of %d (%.2f%%)",
            archive.upper(),
            other.upper(),
            resolved,
            total,
            resolved / total * 100 if total else 0,
        )
        counted[f"references_out_of_{archive}"] = {
            "unresolved": unresolved,
            f"resolved_by_{other}": resolved,
            "total": total,
        }
        write_venn(
            VennCounts(nb_only=unresolved, ia_only=0, both=resolved),
            f"References out of {archive.upper()}",
            args.out_dir / f"references_out_of_{archive}.png",
            set_labels=("", f"Resolved by {other.upper()}"),
            show_total=True,
        )

    counts_file = args.out_dir / "outside_archive_references.json"
    counts_file.write_text(
        json.dumps(
            {
                "ghost_cited_by_ia_only": results["ghost_cited_by_ia_only"],
                "ghost_cited_by_nb_only": results["ghost_cited_by_nb_only"],
                "ghost_cited_by_both": results["ghost_cited_by_both"],
                "ia_refs_resolved_by_nb": results["ia_refs_resolved_by_nb"],
                "nb_refs_resolved_by_ia": results["nb_refs_resolved_by_ia"],
                **counted,
            },
            indent=2,
        )
    )
    logger.info("Wrote counts to %s", counts_file)

    connection.close()


if __name__ == "__main__":
    main()
