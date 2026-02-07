import argparse
import logging
from collections import Counter
from pathlib import Path

import pandas as pd
from email.utils import parseaddr
from tqdm import tqdm

from usenet_no.mbox_utils import get_messages_from_field
from usenet_no.make_user_mapping import collect_emails_and_names, get_hash

logger = logging.getLogger(__name__)


def count_posts_per_user_in_mbox_file(
    mbox_file: Path, user_post_counts: Counter[tuple[str, str]]
) -> None:
    """
    Reads messages in mbox_file and add the number of posts per user to user_post_counts
    """
    for message_from in get_messages_from_field(mbox_file=mbox_file):
        name, email = parseaddr(message_from or "")
        user_post_counts[(name, email)] += 1


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
        default=Path("data/messages_per_user.csv"),
        help="Path to CSV output file",
    )
    parser.add_argument(
        "--mappings-directory",
        type=Path,
        default=Path("data/hidden"),
        help="Directory containing email_to_hash.csv and name_to_hash.csv",
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

    # Load or create hash mappings
    args.mappings_directory.mkdir(exist_ok=True, parents=True)
    email_hashes_file = args.mappings_directory / "email_to_hash.csv"
    name_hashes_file = args.mappings_directory / "name_to_hash.csv"

    if not email_hashes_file.exists() or not name_hashes_file.exists():
        logger.info("Mapping files not found, creating them...")
        emails, names = collect_emails_and_names(args.directory, args.limit)
        email_to_hash = {email: get_hash(email) for email in emails}
        name_to_hash = {name: get_hash(name) for name in names}
        pd.DataFrame(
            {"email": email_to_hash.keys(), "hashed_email": email_to_hash.values()}
        ).to_csv(email_hashes_file, index=False)
        pd.DataFrame(
            {"name": name_to_hash.keys(), "hashed_name": name_to_hash.values()}
        ).to_csv(name_hashes_file, index=False)
    else:
        email_to_hash = dict(
            pd.read_csv(email_hashes_file).itertuples(index=False, name=None)
        )
        name_to_hash = dict(
            pd.read_csv(name_hashes_file).itertuples(index=False, name=None)
        )

    user_post_counts: Counter[tuple[str, str]] = Counter()
    mbox_files = sorted(args.directory.glob("*.mbox"))

    for index, mbox_file in enumerate(
        tqdm(
            mbox_files,
            total=args.limit or len(mbox_files),
            desc="Counting posts per user in mbox files",
        )
    ):
        if index == args.limit:
            break
        count_posts_per_user_in_mbox_file(mbox_file, user_post_counts=user_post_counts)
        logger.debug("Processed %s", mbox_file.name)
        df = pd.DataFrame(
            [
                {
                    "hashed_name": name_to_hash.get(name, ""),
                    "hashed_email": email_to_hash.get(email, ""),
                    "post_count": count,
                }
                for (name, email), count in user_post_counts.items()
            ]
        )
        df.to_csv(args.output_file, index=False)

    logger.info(
        "Total unique users: %d. See counts per user in %s",
        len(user_post_counts),
        args.output_file,
    )
