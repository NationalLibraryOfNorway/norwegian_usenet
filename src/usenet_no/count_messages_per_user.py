import mailbox
import re
from collections import Counter
from pathlib import Path
import csv
import argparse
from email import policy
from email.parser import BytesParser


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
    Counts the number of posts per user (email) in an MBOX file.
    """
    try:
        mbox = mailbox.mbox(str(mbox_file), factory=message_factory)
        unique_users = set()
        for message in mbox:
            from_field = message["From"]
            if from_field:
                email = extract_email(str(from_field))
                if email:
                    user_post_counts[email] += 1
                    unique_users.add(email)

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
        writer.writerow(["email", "post_count"])
        for email, count in user_post_counts.items():
            writer.writerow([email, count])
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

    args = parser.parse_args()

    directory = args.directory
    output_file = args.output_file

    user_post_counts = Counter()

    for mbox_file in directory.glob("*.mbox"):
        count_posts_per_user_in_mbox_file(mbox_file, user_post_counts=user_post_counts)

    print(f"Total unique users: {len(user_post_counts)}")

    # Export to CSV
    export_user_post_counts_to_csv(user_post_counts, output_file)
