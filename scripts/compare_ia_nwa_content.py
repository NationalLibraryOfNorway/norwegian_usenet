import argparse
import logging
import mailbox
from pathlib import Path

import pandas as pd
from tqdm import tqdm

from usenet_no.mbox_utils import get_message_bodies

logger = logging.getLogger(__name__)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Compare message content between IA and NWA mbox archives"
    )
    parser.add_argument(
        "--ia-directory",
        type=Path,
        default=Path("data/utf_8_data"),
        help="Directory containing IA mbox files",
    )
    parser.add_argument(
        "--nwa-directory",
        type=Path,
        default=Path("data/temp"),
        help="Directory containing NWA mbox files",
    )
    parser.add_argument(
        "--output-file",
        type=Path,
        default=Path("data/ia_nwa_content_comparison.csv"),
        help="Path to CSV output file",
    )
    parser.add_argument(
        "--overwrite",
        action="store_true",
        help="If flagged, will overwrite existing output file instead of skipping",
    )

    args = parser.parse_args()
    logger.info("Args: %s", args)

    if args.output_file.exists() and not args.overwrite:
        logger.info(
            "Output file already exists: %s. Use --overwrite to regenerate.",
            args.output_file,
        )
        exit(0)

    ia_files = set(args.ia_directory.glob("*.mbox"))
    nwa_files = set(args.nwa_directory.glob("*.mbox"))

    ia_names = {f.name for f in ia_files}
    nwa_names = {f.name for f in nwa_files}
    common_names = ia_names & nwa_names

    ia_only_files = {f for f in ia_files if f.name not in common_names}
    nwa_only_files = {f for f in nwa_files if f.name not in common_names}

    logger.info(
        "IA files: %d, NWA files: %d, common: %d",
        len(ia_files),
        len(nwa_files),
        len(common_names),
    )

    rows = []

    for name in tqdm(
        sorted(common_names), desc="Comparing message overlap in common mbox files"
    ):
        ia_bodies = get_message_bodies(args.ia_directory / name)
        nwa_bodies = get_message_bodies(args.nwa_directory / name)
        rows.append(
            {
                "newsgroup": Path(name).stem,
                "ia_only": len(ia_bodies - nwa_bodies),
                "nwa_only": len(nwa_bodies - ia_bodies),
                "both": len(ia_bodies & nwa_bodies),
            }
        )

    for f in tqdm(ia_only_files, desc="Counting IA-only messages"):
        rows.append(
            {
                "newsgroup": f.stem,
                "ia_only": len(mailbox.mbox(str(f))),
                "nwa_only": 0,
                "both": 0,
            }
        )

    for f in tqdm(nwa_only_files, desc="Counting NWA-only messages"):
        rows.append(
            {
                "newsgroup": f.stem,
                "ia_only": 0,
                "nwa_only": len(mailbox.mbox(str(f))),
                "both": 0,
            }
        )

    pd.DataFrame(rows).sort_values("newsgroup").to_csv(args.output_file, index=False)
    logger.info("Wrote %d rows to %s", len(rows), args.output_file)
