import argparse
import logging
from pathlib import Path
from tqdm import tqdm
import json

from usenet_no.mbox_utils import get_threads

logger = logging.getLogger(__name__)


def extract_thread_data(mbox_file: Path):
    threads = get_threads(mbox_file)
    thread_data = [
        {
            "thread_subject": thread[0].get("Subject", "empty subject"),
            "num_messages": len(thread),
        }
        for thread in threads
    ]
    return {"mbox_file": mbox_file.name, "thread_data": thread_data}


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Count threads per Usenet group")
    parser.add_argument(
        "--directory",
        "-d",
        type=Path,
        default=Path("data/utf_8_data/"),
        help="Directory containing .mbox files",
    )
    parser.add_argument(
        "--output-file",
        "-o",
        type=Path,
        default=Path("data/threads_per_group.jsonl"),
        help="Path to JSONL output file",
    )
    args = parser.parse_args()

    mbox_files = list(args.directory.glob("*.mbox"))
    for mbox_file in tqdm(
        mbox_files,
        desc="Extracting threads from mbox files",
    ):
        thread_data = extract_thread_data(mbox_file)
        with args.output_file.open("a", encoding="utf-8") as f:
            f.write(json.dumps(thread_data) + "\n")
