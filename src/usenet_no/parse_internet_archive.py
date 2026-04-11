import logging
import mailbox
from pathlib import Path

import cchardet as chardet

from usenet_no.mbox_utils import message_factory, write_mbox

logger = logging.getLogger(__name__)


def iter_message_texts(mbox_file: Path, encoding: str, error_handler: str):
    """Yield each message in mbox_file as a decoded string."""
    mbox_in = mailbox.mbox(str(mbox_file), factory=message_factory)
    for key in mbox_in.keys():
        yield mbox_in.get_bytes(key).decode(encoding, errors=error_handler)


def process_mbox_file(
    mbox_file: Path, outfile: Path, error_handler: str
) -> tuple[str, str]:
    """Detect encoding, normalize and write mbox file. Returns (stem, encoding)."""
    try:
        [e for e in mailbox.mbox(mbox_file)]
        encoding = "utf-8"
        logger.debug("Detected UTF-8 encoding for %s", mbox_file.name)
    except UnicodeDecodeError:
        detection = chardet.detect(mbox_file.read_bytes())
        encoding = detection.get("encoding")
        logger.debug("Re-encoding %s from %s to UTF-8", mbox_file.name, encoding)

    write_mbox(iter_message_texts(mbox_file, encoding, error_handler), outfile)
    return mbox_file.stem, encoding
