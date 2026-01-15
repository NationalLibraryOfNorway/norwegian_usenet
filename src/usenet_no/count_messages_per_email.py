import mailbox
from collections import Counter
from pathlib import Path
import argparse

from tqdm import tqdm
import pandas as pd

import logging
from usenet_no.mbox_utils import message_factory
from email.utils import parseaddr


logger = logging.getLogger(__name__)


def count_posts_per_email_in_mbox_file(
    mbox_file: Path, email_post_counts: Counter[str]
) -> None:
    """
    Reads messages in mbox_file and add the number of posts per email to email_post_counts
    """
    try:
        mbox = mailbox.mbox(str(mbox_file), factory=message_factory)
        for message in mbox:
            message_from = message["From"] or message.get_from()
            if not message_from:
                logger.warning("Message has no from: %s", dir(message))
                continue
            name, email = parseaddr(message_from)
            if not email:
                logger.warning("No email adress found in from field: %s", message_from)
                continue
            email_post_counts[email] += 1

    except Exception as e:
        logger.warning("Error processing file %s \t %s \t %s", (mbox_file, type(e)), e)


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
        default=Path("data/count_messages_per_email.csv"),
        help="Path to CSV output file",
    )
    parser.add_argument(
        "--user-count-file",
        type=Path,
        default=Path("data/count_messages_per_user.csv"),
        help="CSV file with output of count_messages_per_user.py (this contains emails too)",
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
            "Total unique emails: %d. See counts per email in %s",
            len(args.output_file.read_text().splitlines()),
            args.output_file,
        )
        exit(0)

    if args.user_count_file.exists() and not args.overwrite:
        logger.info("Reading emails from user count file %s", args.user_count_file)
        df = pd.read_csv(str(args.user_count_file))
        email_counts_df = (
            df.dropna(subset=["email"])
            .groupby("email", as_index=False)["post_count"]
            .sum()
        ).sort_values("post_count")

        email_counts_df.to_csv(args.output_file, index=False)

        logger.info(
            "Total unique emails: %d. See counts per email in %s",
            len(email_counts_df),
            args.output_file,
        )
        exit(0)

    email_post_counts = Counter()
    mbox_files = list(args.directory.glob("*.mbox"))

    for i, mbox_file in enumerate(
        tqdm(
            mbox_files,
            total=args.limit or len(mbox_files),
            desc="Add email message counts from all mbox files",
        )
    ):
        if args.limit and i == args.limit:
            break
        count_posts_per_email_in_mbox_file(
            mbox_file, email_post_counts=email_post_counts
        )

    email_counts_df = pd.DataFrame(
        {"email": email_post_counts.keys(), "post_count": email_post_counts.values()}
    ).sort_values("post_count")

    email_counts_df.to_csv(args.output_file, index=False)

    logger.info(
        "Total unique emails: %d. See counts per email in %s",
        len(email_post_counts),
        args.output_file,
    )
