import argparse
import logging
import mailbox
from pathlib import Path

import pandas as pd
from tqdm import tqdm

from usenet_no.mbox_utils import get_message_bodies

logger = logging.getLogger(__name__)


def compare_content(ia_directory: Path, nb_directory: Path) -> list[dict]:
    """Compare message body overlap per newsgroup between an IA and an NB directory."""
    ia_files = set(ia_directory.glob("*.mbox"))
    nb_files = set(nb_directory.glob("*.mbox"))

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
        ia_bodies = get_message_bodies(ia_directory / name)
        nb_bodies = get_message_bodies(nb_directory / name)
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

    return rows


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
        "--ia-date-filtered-directory",
        type=Path,
        default=Path("data/internet_archive/date_filtered"),
        help="Directory containing date-filtered IA mbox files",
    )
    parser.add_argument(
        "--nb-directory",
        type=Path,
        default=Path("data/nb/utf_8_data"),
        help="Directory containing NB mbox files",
    )
    parser.add_argument(
        "--full-output-file",
        type=Path,
        default=Path("data/ia_nb_content_comparison.csv"),
        help="Path to CSV output file for the full IA archive comparison",
    )
    parser.add_argument(
        "--date-filtered-output-file",
        type=Path,
        default=Path("data/ia_nb_content_comparison_date_filtered.csv"),
        help="Path to CSV output file for the date-filtered IA archive comparison",
    )
    parser.add_argument(
        "--overwrite",
        action="store_true",
        help="If flagged, will overwrite existing output files instead of skipping",
    )

    args = parser.parse_args()
    logger.info("Args: %s", args)

    for ia_directory, output_file in [
        (args.ia_directory, args.full_output_file),
        (args.ia_date_filtered_directory, args.date_filtered_output_file),
    ]:
        if output_file.exists() and not args.overwrite:
            logger.info(
                "Output file already exists: %s. Use --overwrite to regenerate.",
                output_file,
            )
            continue

        rows = compare_content(
            ia_directory=ia_directory, nb_directory=args.nb_directory
        )

        pd.DataFrame(rows).sort_values("newsgroup").to_csv(output_file, index=False)
        logger.info("Wrote %d rows to %s", len(rows), output_file)
