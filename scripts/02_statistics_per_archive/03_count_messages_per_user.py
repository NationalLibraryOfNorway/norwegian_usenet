import argparse
import logging
from collections import Counter
from concurrent.futures import ProcessPoolExecutor, as_completed
from pathlib import Path

import pandas as pd
from email.utils import parseaddr
from tqdm import tqdm

from usenet_no.mbox_utils import get_messages_from_field
from usenet_no.hash import get_hash_dict

logger = logging.getLogger(__name__)


def count_posts_per_user_in_mbox_file(mbox_file: Path) -> Counter[tuple[str, str]]:
    """Return a Counter of (name, email) -> post count for all messages in mbox_file."""
    counts: Counter[tuple[str, str]] = Counter()
    for message_from in get_messages_from_field(
        mbox_file=mbox_file, show_progress=False
    ):
        name, email = parseaddr(message_from or "")
        counts[(name, email)] += 1
    return counts


def count_posts_per_user_in_directory(
    directory: Path, limit: int | None
) -> Counter[tuple[str, str]]:
    """Count posts per (name, email) across all mbox files in a directory, in parallel."""
    mbox_files = sorted(directory.glob("*.mbox"))[:limit]
    user_post_counts: Counter[tuple[str, str]] = Counter()

    with ProcessPoolExecutor() as executor:
        futures = {
            executor.submit(count_posts_per_user_in_mbox_file, f): f for f in mbox_files
        }
        for future in tqdm(
            as_completed(futures), total=len(futures), desc="Counting posts per user"
        ):
            user_post_counts += future.result()

    return user_post_counts


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Count messages per user")
    parser.add_argument(
        "--nb-directory",
        type=Path,
        default=Path("data/nb/utf_8_data"),
        help="Directory containing Nasjonalbiblioteket (NB) .mbox files",
    )
    parser.add_argument(
        "--ia-directory",
        type=Path,
        default=Path("data/internet_archive/utf_8_data"),
        help="Directory containing Internet Archive (IA) .mbox files",
    )
    parser.add_argument(
        "--ia-date-filtered-directory",
        type=Path,
        default=Path("data/internet_archive/date_filtered"),
        help="Directory containing date-filtered Internet Archive (IA) .mbox files",
    )
    parser.add_argument(
        "--nb-output-file",
        type=Path,
        default=Path("data/messages_per_user_nb.csv"),
        help="Path to CSV output file for NB user counts",
    )
    parser.add_argument(
        "--ia-output-file",
        type=Path,
        default=Path("data/messages_per_user_ia.csv"),
        help="Path to CSV output file for IA user counts",
    )
    parser.add_argument(
        "--ia-date-filtered-output-file",
        type=Path,
        default=Path("data/messages_per_user_ia_date_filtered.csv"),
        help="Path to CSV output file for date-filtered IA user counts",
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

    email_hashes_file = args.mappings_directory / "email_to_hash.csv"
    name_hashes_file = args.mappings_directory / "name_to_hash.csv"

    if not email_hashes_file.exists() or not name_hashes_file.exists():
        logger.error(
            "Mapping files not found in %s. Run 02_hash_user_emails_and_names.py first.",
            args.mappings_directory,
        )
        exit(1)

    email_to_hash = get_hash_dict(email_hashes_file)
    name_to_hash = get_hash_dict(name_hashes_file)

    for directory, output_file in [
        (args.nb_directory, args.nb_output_file),
        (args.ia_directory, args.ia_output_file),
        (args.ia_date_filtered_directory, args.ia_date_filtered_output_file),
    ]:
        if output_file.exists() and not args.overwrite:
            logger.info(
                "Existing file found at %s; use --overwrite to regenerate",
                output_file,
            )
            continue

        user_post_counts = count_posts_per_user_in_directory(directory, args.limit)

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
        df.sort_values(["hashed_email", "hashed_name"], ignore_index=True).to_csv(
            output_file, index=False
        )
        logger.info(
            "Total unique users in %s: %d. See counts per user in %s",
            directory,
            len(user_post_counts),
            output_file,
        )
