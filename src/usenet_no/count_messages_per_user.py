import mailbox
import re
from collections import Counter
from pathlib import Path
import csv
import argparse
from email import policy
from email.parser import BytesParser
from tqdm import tqdm


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
        unique_users = set()
        for message in mbox:
            message_from = message["From"] or message.get_from()
            if not message_from:
                print(f"Message has no from\n{message}")
                print(dir(message))
                message_from = "unknown"
            user_post_counts[message_from] += 1
            unique_users.add(message_from)

        print(
            f"Processed {mbox_file.name}: {len(unique_users)} unique users in this file."
        )

    except Exception as e:
        print(f"Error processing {mbox_file}: {e}")


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
    print(f"Exported results to {output_file}")


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
        "--limit",
        type=int,
        metavar="N",
        default=None,
        help="If passed, will only count messages for the first N mbox files",
    )

    args = parser.parse_args()

    directory = args.directory
    output_file = args.output_file

    user_post_counts = Counter()

    mbox_files = list(directory.glob("*.mbox"))

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

    print(f"Total unique users: {len(user_post_counts)}")

    # Export to CSV
    export_user_post_counts_to_csv(user_post_counts, output_file)
