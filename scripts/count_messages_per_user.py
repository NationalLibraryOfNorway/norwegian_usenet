import argparse
import logging
from collections import Counter
from pathlib import Path

import pandas as pd
from email.utils import parseaddr
from tqdm import tqdm

from usenet_no.mbox_utils import get_messages_from_field

logger = logging.getLogger(__name__)


def count_posts_per_user_in_mbox_file(
    mbox_file: Path, user_post_counts: Counter[tuple[str, str, str]]
) -> None:
    """
    Reads messages in mbox_file and add the number of posts per user to user_post_counts
    """
    for message_from in get_messages_from_field(mbox_file=mbox_file):
        if not message_from:
            message_from = "unknown"
        name, email = parseaddr(message_from)
        user_post_counts[(message_from, name, email)] += 1


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Count messages per user")
    parser.add_argument(
        "--directory",
        type=Path,
        default=Path("data/utf_8_data"),
        help="Directory containing .mbox files",
    )
    parser.add_argument(
        "--output-file",
        type=Path,
        default=Path("data/count_messages_per_user.csv"),
        help="Path to CSV output file",
    )
    parser.add_argument(
        "--overwrite",
        action="store_true",
        help="If flagged, will overwrite existing files instead of skipping",
    )
    parser.add_argument(
        "--limit",
        type=int,
        metavar="N",
        default=None,
        help="If passed, will only count messages for the first N mbox files",
    )

    args = parser.parse_args()
    logger.info("Args: %s", args)

    if args.output_file.exists() and not args.overwrite:
        logger.info(
            "Total unique users: %d. See counts per user in %s",
            len(args.output_file.read_text().splitlines()),
            args.output_file,
        )
        exit(0)

    user_post_counts: Counter[tuple[str, str, str]] = Counter()
    mbox_files = sorted(args.directory.glob("*.mbox"))

    for index, mbox_file in enumerate(
        tqdm(mbox_files, total=args.limit or len(mbox_files))
    ):
        if index == args.limit:
            break
        count_posts_per_user_in_mbox_file(mbox_file, user_post_counts=user_post_counts)
        logger.debug("Processed %s", mbox_file.name)
        df = pd.DataFrame(
            [
                {
                    "from": message_from,
                    "name": name,
                    "email": email,
                    "post_count": count,
                }
                for (message_from, name, email), count in user_post_counts.items()
            ]
        )
        df.to_csv(args.output_file, index=False)

    logger.info(
        "Total unique users: %d. See counts per user in %s",
        len(user_post_counts),
        args.output_file,
    )
