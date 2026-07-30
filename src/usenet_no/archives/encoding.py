"""Encoding detection shared by the two archive parsers.

Neither archive declares its encoding, so both detect one per source file with
chardet, falling back to latin-1, which maps every byte and so never fails.
`detect_file_encoding` streams, for the IA mbox files that run to hundreds of
megabytes; `detect_and_decode_file` reads a file whole. Both parse scripts write
what they detected with `write_file_encodings`.
"""

import json
import logging
from collections.abc import Mapping
from pathlib import Path

import cchardet as chardet

logger = logging.getLogger(__name__)

# Detected encoding per source file, keyed by path relative to unzipped_data.
FileEncodings = dict[str, str]

FALLBACK_ENCODING = "latin-1"

# Undeclared bytes that no encoding maps are kept as visible \xNN escapes rather
# than dropped or turned into U+FFFD, which the IA archive already lost characters to.
UNICODE_ERROR_HANDLER = "backslashreplace"

_IMPLAUSIBLE_ENCODINGS = frozenset({"VISCII", "EUC-TW"})

_CHUNK_SIZE = 1 << 20


def resolve_detected(encoding: str | None, source: object) -> str:
    """Resolve detected encoding (sometimes chardet report implausible encodings for the single-file messages from NB archive)."""
    if encoding is None or encoding in _IMPLAUSIBLE_ENCODINGS:
        logger.debug(
            "Detected %s for %s, reading using fallback encoding %s",
            encoding,
            source,
            FALLBACK_ENCODING,
        )
        return FALLBACK_ENCODING
    return encoding


def detect_chunk_encoding(raw: bytes) -> str:
    """Detect the encoding of one chunk of bytes held in memory."""
    return resolve_detected(
        encoding=chardet.detect(raw).get("encoding"), source="<bytes>"
    )


def detect_file_encoding(file: Path) -> str:
    """Detect the encoding of a whole file, streaming it in chunks (some files are large)"""
    detector = chardet.UniversalDetector()
    with file.open("rb") as stream:
        while chunk := stream.read(_CHUNK_SIZE):
            detector.feed(chunk)
    detector.close()
    return resolve_detected(encoding=detector.result.get("encoding"), source=file)


def decode_bytes(raw: bytes, encoding: str) -> str:
    """Decode bytes to text with an explicit encoding."""
    return raw.decode(encoding, errors=UNICODE_ERROR_HANDLER)


def detect_and_decode_file(file: Path) -> tuple[str, str]:
    """Read one file, returning its text and the encoding detected from its own bytes."""
    raw = file.read_bytes()
    encoding = detect_chunk_encoding(raw)
    return decode_bytes(raw, encoding), encoding


def source_key(source_file: Path, unzipped_dir: Path) -> str:
    """The key a source file is reported under: its path below unzipped_dir."""
    return source_file.relative_to(unzipped_dir).as_posix()


def load_file_encodings(encodings_file: Path) -> FileEncodings:
    """Read the encodings written by an earlier parse, empty if there is none yet."""
    if not encodings_file.exists():
        return {}
    with encodings_file.open(encoding="utf-8") as stream:
        loaded = json.load(stream)
    # The IA parse used to key newsgroup stems to a {"encoding": ...} object.
    encodings = {key: value for key, value in loaded.items() if isinstance(value, str)}
    if len(encodings) < len(loaded):
        logger.warning(
            "Ignoring %d entries in %s that are not source file encodings",
            len(loaded) - len(encodings),
            encodings_file,
        )
    return encodings


def write_file_encodings(encodings: Mapping[str, str], encodings_file: Path) -> None:
    """Write the encoding detected for each source file, keyed by `source_key`.

    Writes nothing when there is nothing to report, which is what a run that
    skipped every source file has, so an empty file never replaces a lost one.
    """
    if not encodings:
        logger.warning("Detected no encodings to write to %s", encodings_file)
        return
    encodings_file.parent.mkdir(parents=True, exist_ok=True)
    with encodings_file.open("w", encoding="utf-8") as stream:
        json.dump(encodings, stream, indent=4, sort_keys=True)
    logger.info(
        "Wrote detected encodings for %d source files to %s",
        len(encodings),
        encodings_file,
    )
