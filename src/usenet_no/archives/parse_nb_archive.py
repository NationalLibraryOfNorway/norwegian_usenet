import csv
import logging
import tarfile
from collections import defaultdict
from collections.abc import Iterable, Iterator
from pathlib import Path

from usenet_no.archives.encoding import detect_and_decode_file
from usenet_no.mbox_utils import RawMessage, write_mbox

logger = logging.getLogger(__name__)


def extract_tarfiles(zipped_dir: Path, unzipped_dir: Path) -> None:
    for compressed_dir in sorted(zipped_dir.glob("*.tar")):
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

    Subdirectories are walked in sorted order: iterdir yields them in the order
    the filesystem holds them, which is not the same on two machines, and the
    first one found is the one descended into.
    """
    # In one of the directories, the parent dir is named NEWS
    if directory.name == "no" or (
        directory.name == "NEWS" and "KZ" in directory.parent.name
    ):
        return directory
    for e in sorted(directory.iterdir()):
        if e.is_dir():
            return find_newsgroups_parent_dir(e)


def iter_newsgroup_sources(
    newsgroup_dir: Path, stem: str, corrections: dict[str, str] | None = None
) -> Iterator[tuple[str, list[Path]]]:
    """Yield (mbox stem, message files) for newsgroup_dir and every subgroup below it.

    corrections maps cut-off mbox file stems to the stem to yield instead (see
    load_newsgroup_corrections), so messages from a cut-off directory land in
    the same output file as the sources that carry the full name. The caller
    corrects the top-level stem itself, with correct_stem.
    """
    message_files = []
    for each in sorted(newsgroup_dir.iterdir()):
        if each.is_dir():
            sub_stem = correct_stem(f"{stem}.{each.name.lower()}", corrections or {})
            yield from iter_newsgroup_sources(each, sub_stem, corrections)
        else:
            message_files.append(each)
    if message_files:
        yield stem, message_files


def count_source_files_per_newsgroup(
    unzipped_dir: Path, corrections: dict[str, str]
) -> dict[str, int]:
    """Count the source files behind each mbox file stem, without reading any of them.

    Walks the extracted NB sources the way
    scripts/01_extract_and_parse_usenet_data/02_parse_nb_archive.py does, so a
    stem is counted over every tar archive that carries the newsgroup.
    """
    counts: dict[str, int] = defaultdict(int)
    for directory in sorted(unzipped_dir.iterdir()):
        if not directory.is_dir():
            continue
        newsgroups_parent_dir = find_newsgroups_parent_dir(directory)
        if newsgroups_parent_dir is None:
            logger.warning("Found no newsgroups directory in %s", directory)
            continue
        for newsgroup_dir in sorted(newsgroups_parent_dir.iterdir()):
            if not newsgroup_dir.is_dir():
                continue
            stem = correct_stem(f"no.{newsgroup_dir.name.lower()}", corrections)
            for sub_stem, message_files in iter_newsgroup_sources(
                newsgroup_dir, stem, corrections
            ):
                counts[sub_stem] += len(message_files)
    return dict(counts)


def write_messages_to_mbox(
    message_files: Iterable[Path], outfile: Path
) -> dict[Path, str]:
    """Decode message files and append them to outfile, returning the encoding of each.

    A source file holds one message with no envelope line, so write_mbox writes
    the placeholder one and the whole file is the message's text.
    """
    encodings = {}
    messages = []
    for message_file in message_files:
        text, encoding = detect_and_decode_file(message_file)
        messages.append(RawMessage(envelope=None, text=text))
        encodings[message_file] = encoding
    write_mbox(messages, outfile, append=True)
    logger.info("Wrote %d textfiles to %s", len(messages), outfile)
    return encodings


def build_mbox_files_from_single_message_textfiles(
    newsgroup_dir: Path,
    outfile: Path,
    corrections: dict[str, str] | None = None,
) -> dict[Path, str]:
    """Write newsgroup_dir and its subgroups to mbox files, one per newsgroup.

    Returns the encoding detected for each message file written. Output files are
    appended to, since several tar archives can carry the same newsgroup.
    """
    logger.debug(
        "Running build_mbox_files_from_single_message_textfiles in %s (outfile: %s)",
        newsgroup_dir,
        outfile,
    )
    encodings: dict[Path, str] = {}
    for stem, message_files in iter_newsgroup_sources(
        newsgroup_dir, outfile.stem, corrections
    ):
        target = outfile.parent / f"{stem}.mbox"
        encodings.update(write_messages_to_mbox(message_files, target))
    return encodings
