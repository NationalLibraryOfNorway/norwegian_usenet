import argparse
import logging
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

import pandas as pd
from email.utils import parseaddr
from tqdm import tqdm

from usenet_no.mbox_utils import get_messages_from_field
from usenet_no.hash import make_hash

logger = logging.getLogger(__name__)


def collect_names_and_emails_from_mbox_file(
    mbox_file: Path,
) -> tuple[set[str], set[str]]:
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
            executor.map(collect_names_and_emails_from_mbox_file, mbox_files),
            total=len(mbox_files),
            desc="Collecting emails and names",
        ):
            emails |= file_emails
            names |= file_names
    return emails, names


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Create hashes for emails and names from both archives, so we can report user statistics without sharing full names and emails."
    )
    parser.add_argument(
        "--ia-directory",
        type=Path,
        default=Path("data/internet_archive/utf_8_data"),
        help="Directory containing Internet Archive (IA) .mbox files",
    )
    parser.add_argument(
        "--nb-directory",
        type=Path,
        default=Path("data/nb/utf_8_data"),
        help="Directory containing Nasjonalbiblioteket (NB) .mbox files",
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

    if email_hashes_file.exists() and name_hashes_file.exists() and not args.overwrite:
        logger.info("Files already exist, use --overwrite to regenerate")
        exit(0)

    emails_to_hash: set[str] = set()
    names_to_hash: set[str] = set()
    for directory in [args.ia_directory, args.nb_directory]:
        directory_emails, directory_names = collect_emails_and_names(
            directory, args.limit
        )
        emails_to_hash |= directory_emails
        names_to_hash |= directory_names

    # Hash all collected emails
    hashed_emails = {email: make_hash(email) for email in emails_to_hash}
    assert len(set(hashed_emails.values())) == len(hashed_emails), (
        "Non-unique hash values for emails"
    )

    # Hash all collected names
    hashed_names = {name: make_hash(name) for name in names_to_hash}
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
