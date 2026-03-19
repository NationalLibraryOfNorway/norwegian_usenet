import mailbox

from usenet_no.mbox_utils import resolve_root_id


def make_msg(msg_id: str, references: list[str]) -> mailbox.mboxMessage:
    msg = mailbox.mboxMessage()
    msg["Message-ID"] = msg_id
    if references:
        msg["References"] = " ".join(references)
    return msg


def test_root_returns_itself():
    msg = make_msg(msg_id="<A>", references=[])
    id_to_msg = {"<A>": msg}
    root_ids = {"<A>"}
    assert resolve_root_id("<A>", id_to_msg, root_ids, {}) == "<A>"


def test_direct_reply_to_root():
    id_to_msg = {
        "<A>": make_msg(msg_id="<A>", references=[]),
        "<B>": make_msg(msg_id="<B>", references=["<A>"]),
    }
    root_ids = {"<A>"}
    assert resolve_root_id("<B>", id_to_msg, root_ids, {}) == "<A>"


def test_deep_chain_only_immediate_parent_in_references():
    # A is root, B replies to A, C replies to B
    # C's References only lists B (not A) — the problematic case
    id_to_msg = {
        "<A>": make_msg(msg_id="<A>", references=[]),
        "<B>": make_msg(msg_id="<B>", references=["<A>"]),
        "<C>": make_msg(msg_id="<C>", references=["<B>"]),
    }
    root_ids = {"<A>"}
    assert resolve_root_id("<C>", id_to_msg, root_ids, {}) == "<A>"


def test_reference_not_in_file_makes_message_its_own_root():
    # B references <EXTERNAL> which is not in the file — B is its own root
    id_to_msg = {"<B>": make_msg(msg_id="<B>", references=["<EXTERNAL>"])}
    root_ids = {"<B>"}
    assert resolve_root_id("<B>", id_to_msg, root_ids, {}) == "<B>"


def test_cycle_returns_none():
    # A references B, B references A — cycle, no root reachable
    id_to_msg = {
        "<A>": make_msg(msg_id="<A>", references=["<B>"]),
        "<B>": make_msg(msg_id="<B>", references=["<A>"]),
    }
    root_ids = set()
    assert resolve_root_id("<A>", id_to_msg, root_ids, {}) is None


def test_path_compression_caches_intermediate_nodes():
    # After resolving C, both B and C should be in cache pointing to A
    id_to_msg = {
        "<A>": make_msg(msg_id="<A>", references=[]),
        "<B>": make_msg(msg_id="<B>", references=["<A>"]),
        "<C>": make_msg(msg_id="<C>", references=["<B>"]),
    }
    root_ids = {"<A>"}
    cache: dict[str, str | None] = {}
    resolve_root_id("<C>", id_to_msg, root_ids, cache)
    assert cache["<B>"] == "<A>"
    assert cache["<C>"] == "<A>"


def test_uses_existing_cache_entry():
    # B is already resolved in cache — should not traverse further
    id_to_msg = {
        "<A>": make_msg(msg_id="<A>", references=[]),
        "<B>": make_msg(msg_id="<B>", references=["<A>"]),
        "<C>": make_msg(msg_id="<C>", references=["<B>"]),
    }
    root_ids = {"<A>"}
    cache: dict[str, str | None] = {"<B>": "<A>"}
    assert resolve_root_id("<C>", id_to_msg, root_ids, cache) == "<A>"
