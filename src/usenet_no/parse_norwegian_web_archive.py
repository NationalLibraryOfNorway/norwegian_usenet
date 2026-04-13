import logging
from pathlib import Path

import cchardet as chardet

from usenet_no.mbox_utils import write_mbox

logger = logging.getLogger(__name__)


def find_newsgroups_parent_dir(directory: Path) -> Path:
    """Find the parent directory to all the newsgroups directories"""
    # In one of the directories, the parent dir is named NEWS
    if directory.name == "no" or (
        directory.name == "NEWS" and "KZ" in directory.parent.name
    ):
        return directory
    for e in directory.iterdir():
        if e.is_dir():
            return find_newsgroups_parent_dir(e)


def read_text(text_file: Path) -> str:
    """Read text from a textfile that may not be utf-8 encoded."""
    detection = chardet.detect(text_file.read_bytes())
    encoding = detection.get("encoding")
    if encoding in {"VISCII", "EUC-TW", None}:
        logger.debug(
            "Detected encoding %s for file %s. Trying to decode with latin-1",
            encoding,
            text_file,
        )
        logger.debug("bytes: %s", text_file.read_bytes())
        encoding = "latin-1"

    return text_file.read_bytes().decode(encoding, errors="backslashreplace")


def concat_textfiles(
    newsgroup_dir: Path, outfile: Path, pre_existing: set[str]
) -> None:
    """Read all message files in newsgroup_dir and append them to outfile.

    pre_existing is the set of output filenames that existed before this run started.
    Files in pre_existing are skipped so incremental re-runs don't double-append,
    while files created during the current run are appended to (supporting multiple
    tar archives contributing to the same newsgroup output file).
    """
    logger.debug("Running concat textfiles in %s (outfile: %s)", newsgroup_dir, outfile)
    messages = []
    for each in sorted(newsgroup_dir.iterdir()):
        if each.is_dir():
            sub_group_outfile = (
                outfile.parent / f"{outfile.stem}.{each.name.lower()}.mbox"
            )
            concat_textfiles(each, outfile=sub_group_outfile, pre_existing=pre_existing)
        else:
            messages.append(read_text(each))

    if messages:
        if outfile.name in pre_existing:
            logger.info("Skipping %s (already exists from previous run)", outfile.name)
            return
        count = write_mbox(messages, outfile, append=True)
        logger.info("Wrote %d textfiles to %s", count, outfile)
