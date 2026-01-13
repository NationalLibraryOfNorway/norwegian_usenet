import mailbox
import re
from collections import Counter
from pathlib import Path
import csv
import argparse
from email import policy
from email.parser import BytesParser
from tqdm import tqdm
import logging


logger = logging.getLogger(__name__)


def extract_email(from_field: str) -> str | None:
    """
    Extracts the email address from the 'From:' field
    """
    match = re.search(r"[\w\.-]+@[\w\.-]+", from_field)
    return match.group(0) if match else None


def message_factory(fp: mailbox._PartialFile) -> mailbox.mboxMessage:
    utf8_message_parser = BytesParser(policy=policy.default.clone(utf8=True))
    return mailbox.mboxMessage(utf8_message_parser.parse(fp))


def count_posts_per_user_in_mbox_file(
    mbox_file: Path, user_post_counts: Counter[str]
) -> None:
    """
    Reads messages in mbox_file and add the number of posts per user to user_post_counts
    """
    try:
        mbox = mailbox.mbox(str(mbox_file), factory=message_factory)
        for message in mbox:
            message_from = message["From"] or message.get_from()
            if not message_from:
                logger.debug("Message has no from: %s", dir(message))
                message_from = "unknown"
            user_post_counts[message_from] += 1

    except Exception as e:
        logger.warning("Error processing file %s \t %s \t %s", (mbox_file, type(e)), e)


def export_user_post_counts_to_csv(
    user_post_counts: Counter[str], output_file: Path
) -> None:
    """
    Exports the user post counts to a CSV file.
    """

    with output_file.open(mode="w", newline="", encoding="utf-8") as file:
        writer = csv.writer(file)
        writer.writerow(["user", "email", "post_count"])
        for user, count in user_post_counts.items():
            email = extract_email(user)
            email_str = email if email else ""
            writer.writerow([user, email_str, count])


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

    user_post_counts = Counter()
    mbox_files = list(args.directory.glob("*.mbox"))

    for i, mbox_file in enumerate(
        tqdm(
            mbox_files,
            total=args.limit or len(mbox_files),
            desc="Add user message counts from all mbox files",
        )
    ):
        if args.limit and i == args.limit:
            break
        count_posts_per_user_in_mbox_file(mbox_file, user_post_counts=user_post_counts)

    # Export to CSV
    export_user_post_counts_to_csv(user_post_counts, args.output_file)

    logger.info(
        "Total unique users: %d. See counts per user in %s",
        len(user_post_counts),
        args.output_file,
    )
