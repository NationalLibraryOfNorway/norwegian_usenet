import mailbox
import csv
from pathlib import Path
import argparse
import logging
from tqdm import tqdm

logger = logging.getLogger(__name__)


def count_messages_in_mbox_file(mbox_file: Path) -> int:
    """
    Counts the number of messages in an MBOX file.
    """
    try:
        mbox = mailbox.mbox(str(mbox_file))
        return len(mbox)
    except Exception as e:
        logger.warning("Error processing %s: %s %s", mbox_file, type(e), e)
        return 0


def count_messages_in_directory(directory: Path) -> dict[str, int]:
    """
    Counts the total number of messages in all MBOX files in a given directory.
    """
    newsgroup_message_counts = {}
    mbox_files = list(directory.glob("*.mbox"))
    for mbox_file in tqdm(
        mbox_files, desc=f"Counting messages per group in {directory}"
    ):
        message_count = count_messages_in_mbox_file(mbox_file)
        newsgroup_message_counts[mbox_file.name] = message_count
        logger.debug("Processed %s: %s messages", mbox_file.name, message_count)

    return newsgroup_message_counts


def export_newsgroup_message_counts_to_csv(
    newsgroup_message_counts: dict[str, int], output_file: Path
):
    """
    Exports the message counts per newsgroup to a CSV file.
    """

    total_messages = sum(newsgroup_message_counts.values())
    with output_file.open(mode="w", newline="", encoding="utf-8") as file:
        writer = csv.writer(file)
        writer.writerow(["newsgroup", "message_count"])

        for newsgroup, count in newsgroup_message_counts.items():
            writer.writerow([newsgroup, count])

        # Add a total row
        writer.writerow(["Total", total_messages])
    logger.info("Exported results to %s", output_file)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Count messages per Usenet group")
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
        default=Path("data/messages_per_group_nb.csv"),
        help="Path to CSV output file for NB message counts",
    )
    parser.add_argument(
        "--ia-output-file",
        type=Path,
        default=Path("data/messages_per_group_ia.csv"),
        help="Path to CSV output file for IA message counts",
    )
    parser.add_argument(
        "--ia-date-filtered-output-file",
        type=Path,
        default=Path("data/messages_per_group_ia_date_filtered.csv"),
        help="Path to CSV output file for date-filtered IA message counts",
    )
    args = parser.parse_args()
    logger.info("Args: %s", args)

    for directory, output_file in [
        (args.nb_directory, args.nb_output_file),
        (args.ia_directory, args.ia_output_file),
        (args.ia_date_filtered_directory, args.ia_date_filtered_output_file),
    ]:
        # Count messages in each newsgroup
        newsgroup_message_counts = count_messages_in_directory(directory)

        # Print total number of messages
        total_messages = sum(newsgroup_message_counts.values())
        logger.info(
            "Total messages across all newsgroups in %s: %d", directory, total_messages
        )

        # Export to CSV
        export_newsgroup_message_counts_to_csv(newsgroup_message_counts, output_file)
        logger.info("Wrote newsgroup message counts to %s", output_file)
