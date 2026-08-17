"""Count how many NB messages carry each message header field.

Reads every source file listed in the encodings file 02_parse_nb_archive.py
wrote, decodes its header block with the encoding detected there, and writes one
row per header field with the number of messages that carry it.
"""

import argparse
import logging
from pathlib import Path

from tqdm import tqdm

from usenet_no.archives.encoding import load_file_encodings
from usenet_no.archives.header_fields import (
    count_header_fields,
    read_header_block,
    write_header_field_counts,
)

logger = logging.getLogger(__name__)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Count the message header fields in the NB source messages",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument(
        "--unzipped-dir",
        type=Path,
        default=Path("data/input/nb/unzipped_data"),
        help="Directory holding the extracted NB sources, one message per file",
    )
    parser.add_argument(
        "--encodings-file",
        type=Path,
        default=Path("data/input/nb/encodings.json"),
        help="JSON file mapping each source file, by its path below --unzipped-dir, to its encoding (02_parse_nb_archive.py)",
    )
    parser.add_argument(
        "--output-file",
        type=Path,
        default=Path(
            "data/output/01_extract_and_parse_usenet_data/nb_header_field_counts.csv"
        ),
        help="CSV file to write the field counts to",
    )

    args = parser.parse_args()
    logging.basicConfig(level=logging.INFO)
    logger.info("Args: %s", args)

    encodings = load_file_encodings(args.encodings_file)
    logger.info(
        "Read %d source file encodings from %s", len(encodings), args.encodings_file
    )

    counts = count_header_fields(
        read_header_block(args.unzipped_dir / key, encoding)
        for key, encoding in tqdm(
            sorted(encodings.items()), desc="Reading message headers"
        )
    )

    write_header_field_counts(counts, args.output_file)
