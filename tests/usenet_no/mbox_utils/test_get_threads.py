import mailbox
import tempfile

from pathlib import Path

from usenet_no.mbox_utils import get_threads


def write_mbox(messages: list[mailbox.mboxMessage]) -> Path:
    f = tempfile.NamedTemporaryFile(suffix=".mbox", delete=False)
    mbox = mailbox.mbox(f.name)
    for msg in messages:
        mbox.add(msg)
    mbox.flush()
    return Path(f.name)


def make_msg(msg_id: str | None, references: list[str]) -> mailbox.mboxMessage:
    msg = mailbox.mboxMessage()
    if msg_id:
        msg["Message-ID"] = msg_id
    if references:
        msg["References"] = " ".join(references)
    return msg


def test_single_message_is_one_thread():
    path = write_mbox([make_msg(msg_id="<A>", references=[])])
    threads = get_threads(path)
    assert len(threads) == 1
    assert len(threads[0]) == 1


def test_two_unrelated_messages_are_two_threads():
    path = write_mbox(
        [make_msg(msg_id="<A>", references=[]), make_msg(msg_id="<B>", references=[])]
    )
    threads = get_threads(path)
    assert len(threads) == 2


def test_reply_groups_with_root():
    path = write_mbox(
        [
            make_msg(msg_id="<A>", references=[]),
            make_msg(msg_id="<B>", references=["<A>"]),
        ]
    )
    threads = get_threads(path)
    assert len(threads) == 1
    assert len(threads[0]) == 2


def test_root_is_first_even_if_reply_appears_first_in_file():
    path = write_mbox(
        [
            make_msg(msg_id="<B>", references=["<A>"]),
            make_msg(msg_id="<A>", references=[]),
        ]
    )
    threads = get_threads(path)
    assert len(threads) == 1
    assert threads[0][0]["Message-ID"] == "<A>"


def test_no_message_id_with_valid_reference_joins_thread():
    path = write_mbox(
        [
            make_msg(msg_id="<A>", references=[]),
            make_msg(msg_id=None, references=["<A>"]),
        ]
    )
    threads = get_threads(path)
    assert len(threads) == 1
    assert len(threads[0]) == 2


def test_no_message_id_and_no_valid_reference_is_stray():
    path = write_mbox(
        [
            make_msg(msg_id="<A>", references=[]),
            make_msg(msg_id=None, references=["<EXTERNAL>"]),
        ]
    )
    threads = get_threads(path)
    stray_thread = [t for t in threads if t[0].get("Message-ID") is None]
    assert len(stray_thread) == 1
