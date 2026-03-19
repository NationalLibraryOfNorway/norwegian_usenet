from email import policy
from email.parser import BytesParser
from tqdm import tqdm

import mailbox
import logging
from collections import defaultdict
from pathlib import Path
from typing import Iterator

logger = logging.getLogger(__name__)


def message_factory(fp: mailbox._PartialFile) -> mailbox.mboxMessage:
    utf8_message_parser = BytesParser(policy=policy.default.clone(utf8=True))
    return mailbox.mboxMessage(utf8_message_parser.parse(fp))


def get_messages_from_field(mbox_file: Path) -> Iterator[str]:
    """Iterates over every message in mbox file and yields the value in the From field of every message"""
    mbox = mailbox.mbox(str(mbox_file), factory=message_factory)
    for message in tqdm(
        mbox, desc=f"Getting From field from each message in {mbox_file}"
    ):
        try:
            message_from = message["From"] or message.get_from()
            yield message_from
        except IndexError:
            logger.debug(
                "IndexError when accessing message From field (From field is probably '=?ISO-8859-15?Q??=')"
            )
            logger.debug("message: %s", message)
            yield ""

        except Exception as e:
            logger.warning(
                "Other exception when accessing message from field: %s %s", type(e), e
            )
            logger.debug("message: %s", message)
            yield ""


def get_messages_date_field(mbox_file: Path) -> Iterator[str | None]:
    mbox = mailbox.mbox(str(mbox_file), factory=message_factory)
    for message in tqdm(mbox, desc=f"Getting dates from each message in {mbox_file}"):
        date_field = message.get("Date", None)
        yield date_field


def resolve_root_id(
    start_id: str,
    id_to_msg: dict[str, mailbox.mboxMessage],
    root_ids: set[str],
    cache: dict[str, str | None],
) -> str | None:
    """Walk the References chain from start_id up to the thread root.

    Uses path compression via cache to avoid redundant traversal.
    Returns None if no root can be determined (e.g. due to a cycle).
    """
    chain = []
    current_id = start_id
    visited: set[str] = set()

    while current_id not in cache:
        if current_id in visited:
            break  # cycle detected
        visited.add(current_id)
        chain.append(current_id)

        if current_id in root_ids:
            cache[current_id] = current_id
            break

        # Follow the first reference that exists in this file (oldest ancestor)
        found_next = False
        for ref_id in id_to_msg[current_id].get("References", "").split():
            if ref_id in id_to_msg:
                current_id = ref_id
                found_next = True
                break

        if not found_next:
            # No in-file ancestor — treat as root
            cache[current_id] = current_id
            break

    root_id = cache.get(current_id)
    for mid in chain:
        cache[mid] = root_id
    return cache.get(start_id)


def get_threads(mbox_file: Path) -> list[list[mailbox.mboxMessage]]:
    """Parse an mbox file and return messages grouped into threads.

    Threading uses the References and Message-ID headers (standard NNTP).
    Each thread is a list of messages, and the first message in each thread is the root (a message with no references to other messages in the file).
    """
    mbox = mailbox.mbox(str(mbox_file), factory=message_factory)
    messages = list(mbox)

    id_to_msg: dict[str, mailbox.mboxMessage] = {}
    num_messages_without_ids = 0
    for msg in messages:
        msg_id = msg.get("Message-ID", "").strip()
        if msg_id:
            id_to_msg[msg_id] = msg
        else:
            num_messages_without_ids += 1

    if num_messages_without_ids:
        logger.info(
            "%d of %d messages have no Message-ID field in %s",
            num_messages_without_ids,
            len(messages),
            mbox_file.name,
        )

    # A message is a root if none of its references exist in this file
    root_ids: set[str] = {
        msg_id
        for msg_id, msg in id_to_msg.items()
        if not any(ref_id in id_to_msg for ref_id in msg.get("References", "").split())
    }

    cache: dict[str, str | None] = {}
    stray_messages = []
    root_id_to_thread: dict[str, list[mailbox.mboxMessage]] = defaultdict(list)

    for msg in messages:
        msg_id = msg.get("Message-ID", "").strip()

        root_id = None

        if msg_id:
            root_id = resolve_root_id(msg_id, id_to_msg, root_ids, cache)
        else:
            # No Message-ID — try to find thread via References
            for ref_id in msg.get("References", "").split():
                if ref_id in id_to_msg:
                    root_id = resolve_root_id(ref_id, id_to_msg, root_ids, cache)
                    break

        if root_id is None:
            stray_messages.append([msg])
            continue

        if msg_id == root_id:
            root_id_to_thread[root_id].insert(0, msg)
        else:
            root_id_to_thread[root_id].append(msg)

    if len(stray_messages):
        logger.debug("Number of stray messages: %d", len(stray_messages))

    return [root_id_to_thread[id] for id in root_id_to_thread] + stray_messages
