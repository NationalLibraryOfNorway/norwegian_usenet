import argparse
import json
import logging
import mailbox
from pathlib import Path

from tqdm import tqdm

from usenet_no.mbox_utils import message_factory, parse_message_id, parse_references

logger = logging.getLogger(__name__)


def collect_ids_from_mbox(mbox_file: Path) -> tuple[set[str], set[str]]:
    """Return (message_ids, referenced_ids) from all messages in an mbox file.

    message_ids: set of Message-ID values present in the file.
    referenced_ids: set of all ids listed in References headers.
    """
    mbox = mailbox.mbox(str(mbox_file), factory=message_factory)
    message_ids: set[str] = set()
    referenced_ids: set[str] = set()
    for message in mbox:
        mid = parse_message_id(message.get("Message-ID"))
        if mid:
            message_ids.add(mid)
        for ref in parse_references(message.get("References")):
            referenced_ids.add(ref)
    return message_ids, referenced_ids


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Compare message-id overlap between IA and NWA mbox archives, and collect external references"
    )
    parser.add_argument(
        "--ia-directory",
        type=Path,
        default=Path("data/internet_archive/utf_8_data"),
        help="Directory containing IA mbox files",
    )
    parser.add_argument(
        "--nwa-directory",
        type=Path,
        default=Path("data/nwa_90s/utf_8_data"),
        help="Directory containing NWA mbox files",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("data/ia_nwa_message_id_overlap.json"),
        help="Path to JSON output file",
    )
    args = parser.parse_args()
    logging.basicConfig(level=logging.INFO)
    logger.info("Args: %s", args)

    ia_files = list(args.ia_directory.glob("*.mbox"))
    nwa_files = list(args.nwa_directory.glob("*.mbox"))

    logger.info("IA files: %d, NWA files: %d", len(ia_files), len(nwa_files))

    ia_ids: set[str] = set()
    ia_refs: set[str] = set()
    for f in tqdm(ia_files, desc="Reading IA message IDs"):
        ids, refs = collect_ids_from_mbox(f)
        ia_ids |= ids
        ia_refs |= refs

    nwa_ids: set[str] = set()
    nwa_refs: set[str] = set()
    for f in tqdm(nwa_files, desc="Reading NWA message IDs"):
        ids, refs = collect_ids_from_mbox(f)
        nwa_ids |= ids
        nwa_refs |= refs

    all_ids = ia_ids | nwa_ids

    # IDs missing from their own archive but present in the other
    ia_resolved_by_nwa = (ia_refs - ia_ids) & nwa_ids
    nwa_resolved_by_ia = (nwa_refs - nwa_ids) & ia_ids

    # References that appear in neither archive, partitioned by who cited them
    ghost_ia_only = (ia_refs - nwa_refs) - all_ids
    ghost_nwa_only = (nwa_refs - ia_refs) - all_ids
    ghost_both = (ia_refs & nwa_refs) - all_ids

    results = {
        # Message ID overlap
        "ia_ids": len(ia_ids),
        "nwa_ids": len(nwa_ids),
        "ids_in_both": len(ia_ids & nwa_ids),
        "ids_ia_only": len(ia_ids - nwa_ids),
        "ids_nwa_only": len(nwa_ids - ia_ids),
        # Cross-archive reference resolution
        "ia_refs_resolved_by_nwa": len(ia_resolved_by_nwa),
        "nwa_refs_resolved_by_ia": len(nwa_resolved_by_ia),
        # Ghost references (cited but in neither archive)
        "ghost_cited_by_ia_only": len(ghost_ia_only),
        "ghost_cited_by_nwa_only": len(ghost_nwa_only),
        "ghost_cited_by_both": len(ghost_both),
    }

    for key, value in results.items():
        logger.info("%-35s %d", key, value)

    args.output.write_text(json.dumps(results, indent=2))
    logger.info("Wrote results to %s", args.output)
