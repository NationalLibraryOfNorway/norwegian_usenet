"""Print newsgroup hierarchies as ASCII trees with message counts."""

import argparse
import csv
from pathlib import Path


class Node:
    def __init__(self):
        self.own_count: int = 0
        self.children: dict[str, "Node"] = {}

    def total(self) -> int:
        return self.own_count + sum(c.total() for c in self.children.values())


def load_counts(csv_path: Path) -> dict[str, int]:
    counts = {}
    with csv_path.open(encoding="utf-8") as f:
        for row in csv.DictReader(f):
            name = row["newsgroup"].removesuffix(".mbox")
            if name == "Total":
                continue
            counts[name] = int(row["message_count"])
    return counts


def build_tree(counts: dict[str, int]) -> Node:
    root = Node()
    for name, count in sorted(counts.items()):
        node = root
        for part in name.split("."):
            node = node.children.setdefault(part, Node())
        node.own_count = count
    return root


def _print_children(node: Node, prefix: str = "") -> None:
    items = list(node.children.items())
    for i, (name, child) in enumerate(items):
        is_last = i == len(items) - 1
        connector = "└── " if is_last else "├── "
        print(f"{prefix}{connector}{name}  ({child.total():,})")
        _print_children(child, prefix + ("    " if is_last else "│   "))


def print_archive(label: str, csv_path: Path) -> None:
    counts = load_counts(csv_path)
    tree = build_tree(counts)
    print(f"\n{label}  ({tree.total():,} messages, {len(counts)} newsgroups)")
    _print_children(tree)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Print newsgroup hierarchy as an ASCII tree with message counts",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument(
        "--ia-csv",
        type=Path,
        default=Path("data/output/03_statistics_per_archive/messages_per_group_ia.csv"),
        help="CSV with IA message counts per newsgroup (default: %(default)s)",
    )
    parser.add_argument(
        "--nb-csv",
        type=Path,
        default=Path("data/output/03_statistics_per_archive/messages_per_group_nb.csv"),
        help="CSV with NB message counts per newsgroup (default: %(default)s)",
    )
    args = parser.parse_args()

    print_archive("IA", args.ia_csv)
    print_archive("NB", args.nb_csv)


if __name__ == "__main__":
    main()
