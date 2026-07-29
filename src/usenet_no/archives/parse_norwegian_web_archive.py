import csv
import logging
import tarfile
from pathlib import Path

import cchardet as chardet

from usenet_no.mbox_utils import write_mbox

logger = logging.getLogger(__name__)


def extract_tarfiles(zipped_dir: Path, unzipped_dir: Path) -> None:
    for compressed_dir in zipped_dir.glob("*.tar"):
        logger.info("Unpacking %s", compressed_dir)
        out_dir = unzipped_dir / compressed_dir.stem
        out_dir.mkdir(parents=True, exist_ok=True)
        with tarfile.open(compressed_dir, "r") as tar:
            tar.extractall(path=out_dir, filter="tar")
        logger.info("Extracted %s to %s", compressed_dir, out_dir)


def load_newsgroup_corrections(corrections_file: Path) -> dict[str, str]:
    """Read the cut-off newsgroup name corrections into a stem-to-stem mapping.

    The file is written by
    scripts/01_extract_and_parse_usenet_data/01_extract_nb_archive_and_find_stubbed_newsgroup_names.py
    and maps mbox file stems like `no.alt.diskusjo` to the full name the
    KZ2001-0147 CD cut them off from, like `no.alt.diskusjoner`. Returns an
    empty mapping when the file does not exist, so the parse can run before the
    corrections have been generated.
    """
    if not corrections_file.exists():
        logger.info(
            "No newsgroup corrections file at %s; keeping names as they are",
            corrections_file,
        )
        return {}
    with corrections_file.open(encoding="utf-8", newline="") as file:
        return {row["cut_off_name"]: row["full_name"] for row in csv.DictReader(file)}


def correct_stem(stem: str, corrections: dict[str, str]) -> str:
    """Return the corrected mbox file stem for a newsgroup, or the stem unchanged."""
    if stem in corrections:
        logger.info("Correcting newsgroup name: %s -> %s", stem, corrections[stem])
        return corrections[stem]
    return stem


def find_newsgroups_parent_dir(directory: Path) -> Path:
    """Find the parent directory to all the newsgroups directories.
    This function is needed because the newsgroups are nested differently depending on which CD the data was stored on
    """
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
    newsgroup_dir: Path,
    outfile: Path,
    pre_existing: set[str],
    corrections: dict[str, str] | None = None,
) -> None:
    """Read all message files in newsgroup_dir and append them to outfile.

    pre_existing is the set of output filenames that existed before this run started.
    Files in pre_existing are skipped so incremental re-runs don't double-append,
    while files created during the current run are appended to (supporting multiple
    tar archives contributing to the same newsgroup output file).

    corrections maps cut-off mbox file stems to the stem to write instead (see
    load_newsgroup_corrections), so messages from a cut-off directory land in
    the same output file as the sources that carry the full name. The caller
    corrects the stem of the top-level outfile itself, with correct_stem.
    """
    logger.debug("Running concat textfiles in %s (outfile: %s)", newsgroup_dir, outfile)
    messages = []
    for each in sorted(newsgroup_dir.iterdir()):
        if each.is_dir():
            sub_stem = correct_stem(
                f"{outfile.stem}.{each.name.lower()}", corrections or {}
            )
            concat_textfiles(
                each,
                outfile=outfile.parent / f"{sub_stem}.mbox",
                pre_existing=pre_existing,
                corrections=corrections,
            )
        else:
            messages.append(read_text(each))

    if messages:
        if outfile.name in pre_existing:
            logger.info("Skipping %s (already exists from previous run)", outfile.name)
            return
        count = write_mbox(messages, outfile, append=True)
        logger.info("Wrote %d textfiles to %s", count, outfile)
