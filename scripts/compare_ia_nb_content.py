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
        description="Compare message content between IA and NB mbox archives"
    )
    parser.add_argument(
        "--ia-directory",
        type=Path,
        default=Path("data/internet_archive/utf_8_data"),
        help="Directory containing IA mbox files",
    )
    parser.add_argument(
        "--nb-directory",
        type=Path,
        default=Path("data/nb/utf_8_data"),
        help="Directory containing NB mbox files",
    )
    parser.add_argument(
        "--output-file",
        type=Path,
        default=Path("data/ia_nb_content_comparison.csv"),
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
    nb_files = set(args.nb_directory.glob("*.mbox"))

    ia_names = {f.name for f in ia_files}
    nb_names = {f.name for f in nb_files}
    common_names = ia_names & nb_names

    ia_only_files = {f for f in ia_files if f.name not in common_names}
    nb_only_files = {f for f in nb_files if f.name not in common_names}

    logger.info(
        "IA files: %d, NB files: %d, common: %d",
        len(ia_files),
        len(nb_files),
        len(common_names),
    )

    rows = []

    for name in tqdm(
        sorted(common_names), desc="Comparing message overlap in common mbox files"
    ):
        ia_bodies = get_message_bodies(args.ia_directory / name)
        nb_bodies = get_message_bodies(args.nb_directory / name)
        rows.append(
            {
                "newsgroup": Path(name).stem,
                "ia_only": len(ia_bodies - nb_bodies),
                "nb_only": len(nb_bodies - ia_bodies),
                "both": len(ia_bodies & nb_bodies),
            }
        )

    for f in tqdm(ia_only_files, desc="Counting IA-only messages"):
        rows.append(
            {
                "newsgroup": f.stem,
                "ia_only": len(mailbox.mbox(str(f))),
                "nb_only": 0,
                "both": 0,
            }
        )

    for f in tqdm(nb_only_files, desc="Counting NB-only messages"):
        rows.append(
            {
                "newsgroup": f.stem,
                "ia_only": 0,
                "nb_only": len(mailbox.mbox(str(f))),
                "both": 0,
            }
        )

    pd.DataFrame(rows).sort_values("newsgroup").to_csv(args.output_file, index=False)
    logger.info("Wrote %d rows to %s", len(rows), args.output_file)
