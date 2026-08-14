"""The newsgroup hierarchy of an archive read as a tree of message counts.

A newsgroup name splits on its dots into a path of nodes, so no.marked.diverse
hangs under no.marked, which hangs under no. A supergroup can have an mbox file
of its own; that file's messages are held by a child node labelled OWN_MBOX_LABEL
so they are counted apart from those of the subgroups.
"""

import csv
import logging
from pathlib import Path

logger = logging.getLogger(__name__)

OWN_MBOX_LABEL = "."


class Node:
    def __init__(self):
        self.own_count: int = 0
        self.children: dict[str, Node] = {}

    def total(self) -> int:
        return self.own_count + sum(c.total() for c in self.children.values())


def load_counts(csv_path: Path) -> dict[str, int]:
    """Messages per newsgroup, read from a messages_per_group table."""
    counts = {}
    with csv_path.open(encoding="utf-8") as f:
        for row in csv.DictReader(f):
            name = row["newsgroup"].removesuffix(".mbox")
            if name == "Total":
                continue
            counts[name] = int(row["message_count"])
    logger.info("Loaded message counts for %d newsgroups", len(counts))
    return counts


def build_tree(counts: dict[str, int], hide_empty_own_mbox: bool = False) -> Node:
    """Build the hierarchy of `counts` as a tree below an unlabelled root node.

    With `hide_empty_own_mbox` a supergroup that has no mbox file of its own is
    left without an OWN_MBOX_LABEL child, instead of one counting no messages.
    """
    root = Node()
    for name, count in sorted(counts.items()):
        node = root
        for part in name.split("."):
            node = node.children.setdefault(part, Node())
        node.own_count = count
    for child in root.children.values():
        _add_own_mbox_child(child, hide_empty_own_mbox)
    return root


def _add_own_mbox_child(node: Node, hide_empty_own_mbox: bool) -> None:
    """Move the count of every node that has children into an OWN_MBOX_LABEL child."""
    for child in node.children.values():
        _add_own_mbox_child(child, hide_empty_own_mbox)
    if node.children and not (hide_empty_own_mbox and node.own_count == 0):
        own_mbox = Node()
        own_mbox.own_count = node.own_count
        node.own_count = 0
        node.children = {OWN_MBOX_LABEL: own_mbox, **node.children}


def tree_lines(
    label: str, counts: dict[str, int], hide_empty_own_mbox: bool = False
) -> list[str]:
    """The tree of `counts` as ASCII lines, headed by `label` and its totals."""
    tree = build_tree(counts, hide_empty_own_mbox)
    header = f"{label}  ({tree.total():,} messages, {len(counts)} newsgroups)"
    return [header, *_child_lines(tree)]


def _child_lines(node: Node, prefix: str = "") -> list[str]:
    lines = []
    items = list(node.children.items())
    for i, (name, child) in enumerate(items):
        is_last = i == len(items) - 1
        connector = "└── " if is_last else "├── "
        lines.append(f"{prefix}{connector}{name}  ({child.total():,})")
        lines.extend(_child_lines(child, prefix + ("    " if is_last else "│   ")))
    return lines
