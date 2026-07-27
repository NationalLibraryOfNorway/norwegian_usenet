"""Count IA messages that look like undeclared quoted-printable, per newsgroup.

Unlike the other scripts here, this reads the IA mbox files directly rather than
the database, because it inspects the raw message bodies and Content-Transfer-
Encoding headers, which the database does not store. A message counts when a
text/plain part declares no real transfer encoding, is pure ASCII, and carries
at least --min-escapes quoted-printable escapes for a Norwegian letter (=E5 for
å, =F8 for ø, =E6 for æ, and the upper-case Å/Ø/Æ). --min-escapes matches the
threshold the body decoder in usenet_no.mbox_utils uses.
"""

import argparse
import csv
import logging
import mailbox
import sys
from pathlib import Path

from tqdm import tqdm

from usenet_no.mbox_utils import message_factory
from usenet_no.quoted_printable import message_is_undeclared_quoted_printable

logger = logging.getLogger(__name__)


def count_undeclared_qp_per_group(
    ia_directory: Path, min_escapes: int
) -> list[tuple[str, int, int]]:
    """Per newsgroup: (newsgroup, undeclared_qp_messages, total_messages)."""
    rows = []
    for mbox_file in tqdm(
        sorted(ia_directory.glob("*.mbox")), desc="Scanning IA mbox files"
    ):
        mbox = mailbox.mbox(str(mbox_file), factory=message_factory)
        qp_count = total = 0
        for message in mbox:
            total += 1
            if message_is_undeclared_quoted_printable(message, min_escapes):
                qp_count += 1
        rows.append((mbox_file.stem, qp_count, total))
    return rows


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Count IA messages that look like undeclared quoted-printable"
    )
    parser.add_argument(
        "--ia-directory",
        type=Path,
        default=Path("data/input/internet_archive/unzipped_data"),
        help="Directory containing Internet Archive (IA) .mbox files",
    )
    parser.add_argument(
        "--output-file",
        type=Path,
        default=Path(
            "data/output/03_statistics_per_archive/undeclared_quoted_printable_ia.csv"
        ),
        help="Path to CSV output file",
    )
    parser.add_argument(
        "--min-escapes",
        type=int,
        default=1,
        help="Minimum Norwegian-letter (=E5/=F8/=E6/...) escapes to count as quoted-printable",
    )
    parser.add_argument(
        "--overwrite",
        action="store_true",
        help="If flagged, will overwrite an existing output file instead of skipping",
    )

    args = parser.parse_args()
    logging.basicConfig(level=logging.INFO)
    logger.info("Args: %s", args)

    if args.output_file.exists() and not args.overwrite:
        logger.info(
            "Output file already exists: %s. Use --overwrite to regenerate.",
            args.output_file,
        )
        sys.exit(0)

    rows = count_undeclared_qp_per_group(args.ia_directory, args.min_escapes)

    with args.output_file.open("w", newline="", encoding="utf-8") as file:
        writer = csv.writer(file)
        writer.writerow(["newsgroup", "undeclared_qp_messages", "total_messages"])
        writer.writerows(
            (f"{newsgroup}.mbox", qp_count, total)
            for newsgroup, qp_count, total in rows
        )
        writer.writerow(
            ["Total", sum(row[1] for row in rows), sum(row[2] for row in rows)]
        )

    total_qp = sum(row[1] for row in rows)
    total_messages = sum(row[2] for row in rows)
    logger.info(
        "%d of %d IA messages look like undeclared quoted-printable"
        " (min-escapes=%d). Wrote %s",
        total_qp,
        total_messages,
        args.min_escapes,
        args.output_file,
    )
