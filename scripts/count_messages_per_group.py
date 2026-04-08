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
    channel_message_counts = {}
    mbox_files = list(directory.glob("*.mbox"))
    for mbox_file in tqdm(mbox_files, desc="Counting messages per group"):
        message_count = count_messages_in_mbox_file(mbox_file)
        channel_message_counts[mbox_file.name] = message_count
        logger.debug("Processed %s: %s messages", mbox_file.name, message_count)

    return channel_message_counts


def export_channel_message_counts_to_csv(
    channel_message_counts: dict[str, int], output_file: Path
):
    """
    Exports the message counts per channel to a CSV file.
    """

    total_messages = sum(channel_message_counts.values())
    with output_file.open(mode="w", newline="", encoding="utf-8") as file:
        writer = csv.writer(file)
        writer.writerow(["channel", "message_count"])

        for channel, count in channel_message_counts.items():
            writer.writerow([channel, count])

        # Add a total row
        writer.writerow(["Total", total_messages])
    logger.info("Exported results to %s", output_file)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Count messages per Usenet group")
    parser.add_argument(
        "--directory",
        "-d",
        type=Path,
        default=Path("data/internet_archive/utf_8_data"),
        help="Directory containing .mbox files",
    )
    parser.add_argument(
        "--output-file",
        "-o",
        type=Path,
        default=Path("data/messages_per_group_ia.csv"),
        help="Path to CSV output file",
    )
    args = parser.parse_args()

    # Count messages in each channel
    channel_message_counts = count_messages_in_directory(args.directory)

    # Print total number of messages
    total_messages = sum(channel_message_counts.values())
    logger.info("Total messages across all channels: %d", total_messages)

    # Export to CSV
    export_channel_message_counts_to_csv(channel_message_counts, args.output_file)
