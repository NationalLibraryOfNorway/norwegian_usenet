"""Count the "From " lines the IA sources leave unescaped in their message bodies.

An mbox file writes ">From " for a body line beginning with "From ", so that
only an envelope line starts a message, and the IA sources do not: mailbox.mbox
splits a message in two at every such body line. The envelope rule the parse
reads them with accepts only a line carrying a Google Groups id, and this counts
the lines that rule passed over, with the header block check that says whether
any of them begins a message after all.
"""

import argparse
import logging
from pathlib import Path

from tqdm import tqdm

from usenet_no.archives.encoding import load_file_encodings
from usenet_no.archives.message_splits import (
    rejected_envelopes,
    write_rejected_envelopes,
)
from usenet_no.mbox_utils import IA_SOURCE_ENVELOPE

logger = logging.getLogger(__name__)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Count the unescaped 'From ' lines in the IA source messages",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument(
        "--unzipped-dir",
        type=Path,
        default=Path("data/input/internet_archive/unzipped_data"),
        help="Directory holding the unzipped IA sources, one mbox file per newsgroup",
    )
    parser.add_argument(
        "--encodings-file",
        type=Path,
        default=Path("data/input/internet_archive/encodings.json"),
        help="JSON file naming each source file the parse read, by its path below --unzipped-dir (04_parse_internet_archive.py)",
    )
    parser.add_argument(
        "--output-file",
        type=Path,
        default=Path(
            "data/output/01_extract_and_parse_usenet_data/ia_unescaped_from_lines.csv"
        ),
        help="CSV file to write one row per unescaped 'From ' line to",
    )

    args = parser.parse_args()
    logging.basicConfig(level=logging.INFO)
    logger.info("Args: %s", args)

    encodings = load_file_encodings(args.encodings_file)
    logger.info(
        "Read %d source file names from %s", len(encodings), args.encodings_file
    )

    write_rejected_envelopes(
        (
            envelope
            for key in tqdm(sorted(encodings), desc="Reading mbox files")
            for envelope in rejected_envelopes(
                args.unzipped_dir / key, IA_SOURCE_ENVELOPE
            )
        ),
        args.output_file,
    )
