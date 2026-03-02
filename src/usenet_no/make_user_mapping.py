import argparse
import hashlib
import logging
from pathlib import Path

import pandas as pd
from email.utils import parseaddr
from tqdm import tqdm

from usenet_no.mbox_utils import get_messages_from_field

logger = logging.getLogger(__name__)


def get_hash(string_to_hash: str) -> str:
    return hashlib.blake2b(string_to_hash.encode("utf-8"), digest_size=8).hexdigest()


def collect_emails_and_names(
    directory: Path, limit: int | None
) -> tuple[set[str], set[str]]:
    """Collect all unique emails and names from mbox files."""
    emails: set[str] = set()
    names: set[str] = set()

    mbox_files = sorted(directory.glob("*.mbox"))
    for index, mbox_file in enumerate(tqdm(mbox_files, total=limit or len(mbox_files))):
        if index == limit:
            break
        for from_field_value in get_messages_from_field(mbox_file=mbox_file):
            name, email = parseaddr(from_field_value)
            if email:
                emails.add(email)
            if name:
                names.add(name)

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
        return

    emails, names = collect_emails_and_names(args.input_directory, args.limit)

    hashed_emails = {email: get_hash(email) for email in emails}
    assert len(set(hashed_emails.values())) == len(hashed_emails), (
        "Non-unique hash values for emails"
    )

    hashed_names = {name: get_hash(name) for name in names}
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
        "Created %s (%d emails) and %s (%d names)",
        email_hashes_file,
        len(emails),
        name_hashes_file,
        len(names),
    )


if __name__ == "__main__":
    main()
