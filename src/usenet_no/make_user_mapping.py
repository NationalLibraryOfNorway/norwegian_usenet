import argparse
import hashlib
import logging
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

import pandas as pd
from email.utils import parseaddr
from tqdm import tqdm

from usenet_no.mbox_utils import get_messages_from_field

logger = logging.getLogger(__name__)


def get_hash(string_to_hash: str) -> str:
    return hashlib.blake2b(string_to_hash.encode("utf-8"), digest_size=8).hexdigest()


def get_hash_dict(file: Path) -> dict:
    return dict(
        pd.read_csv(file, keep_default_na=False).itertuples(index=False, name=None)
    )


def collect_from_single_mbox(mbox_file: Path) -> tuple[set[str], set[str]]:
    emails: set[str] = set()
    names: set[str] = set()
    for from_field_value in get_messages_from_field(mbox_file, show_progress=False):
        name, email = parseaddr(from_field_value or "")
        if email:
            emails.add(email)
        if name:
            names.add(name)
    return emails, names


def collect_emails_and_names(
    directory: Path, limit: int | None
) -> tuple[set[str], set[str]]:
    """Collect all unique emails and names from mbox files in parallel."""
    mbox_files = sorted(directory.glob("*.mbox"))[:limit]
    emails: set[str] = set()
    names: set[str] = set()
    with ProcessPoolExecutor() as executor:
        for file_emails, file_names in tqdm(
            executor.map(collect_from_single_mbox, mbox_files),
            total=len(mbox_files),
            desc="Collecting emails and names",
        ):
            emails |= file_emails
            names |= file_names
    return emails, names


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Create hashed mappings for emails and names"
    )
    parser.add_argument(
        "--input-directory",
        "-i",
        type=Path,
        default=Path("data/utf_8_data"),
        help="Directory containing .mbox files",
    )
    parser.add_argument(
        "--output-directory",
        "-o",
        type=Path,
        default=Path("data/hidden"),
        help="Output directory",
    )
    parser.add_argument(
        "--overwrite",
        action="store_true",
        help="Overwrite existing files",
    )
    parser.add_argument(
        "--extend",
        action="store_true",
        help="Extend existing mappings with new users from input directory",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=None,
        metavar="N",
        help="Only process the first N mbox files",
    )

    args = parser.parse_args()
    logger.info("Args: %s", args)

    args.output_directory.mkdir(exist_ok=True, parents=True)
    email_hashes_file = args.output_directory / "email_to_hash.csv"
    name_hashes_file = args.output_directory / "name_to_hash.csv"

    if (
        email_hashes_file.exists()
        and name_hashes_file.exists()
        and not args.overwrite
        and not args.extend
    ):
        logger.info(
            "Files already exist, use --overwrite to regenerate or --extend to add new users"
        )
        return

    emails_to_hash, names_to_hash = collect_emails_and_names(
        args.input_directory, args.limit
    )

    existing_email_hashes = {}
    existing_name_hashes = {}

    if args.extend and email_hashes_file.exists() and name_hashes_file.exists():
        existing_email_hashes = get_hash_dict(email_hashes_file)
        existing_name_hashes = get_hash_dict(name_hashes_file)
        # Remove emails and names that already have hash values in output files
        emails_to_hash -= set(existing_email_hashes.keys())
        names_to_hash -= set(existing_name_hashes.keys())
        logger.info(
            "Extending mappings with %d new emails and %d new names",
            len(emails_to_hash),
            len(names_to_hash),
        )

    # Hash all emails that are not already hashed
    hashed_emails = existing_email_hashes | {
        email: get_hash(email) for email in emails_to_hash
    }
    assert len(set(hashed_emails.values())) == len(hashed_emails), (
        "Non-unique hash values for emails"
    )

    # Hash all names that are not already hashed
    hashed_names = existing_name_hashes | {
        name: get_hash(name) for name in names_to_hash
    }
    assert len(set(hashed_names.values())) == len(hashed_names), (
        "Non-unique hash values for names"
    )

    pd.DataFrame(
        {"email": hashed_emails.keys(), "hashed_email": hashed_emails.values()}
    ).to_csv(email_hashes_file, index=False)

    pd.DataFrame(
        {"name": hashed_names.keys(), "hashed_name": hashed_names.values()}
    ).to_csv(name_hashes_file, index=False)

    logger.info(
        "Wrote %s (%d emails) and %s (%d names)",
        email_hashes_file,
        len(hashed_emails),
        name_hashes_file,
        len(hashed_names),
    )


if __name__ == "__main__":
    main()
