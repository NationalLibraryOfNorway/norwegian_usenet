"""Write the newsgroup hierarchies as ASCII trees with message counts."""

import argparse
from pathlib import Path

from usenet_no.newsgroup_tree import load_counts, tree_lines


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Write newsgroup hierarchy as an ASCII tree with message counts",
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
    parser.add_argument(
        "-o",
        "--output-dir",
        type=Path,
        default=Path("data/output/03_statistics_per_archive/newsgroup_tree"),
        help="Output directory (default: %(default)s)",
    )
    parser.add_argument(
        "--hide-empty-own-mbox",
        action="store_true",
        help="Draw the '.' child only for supergroups that have an mbox file of their own",
    )
    args = parser.parse_args()

    args.output_dir.mkdir(parents=True, exist_ok=True)
    for label, csv_path in [("ia", args.ia_csv), ("nb", args.nb_csv)]:
        lines = tree_lines(
            label.upper(), load_counts(csv_path), args.hide_empty_own_mbox
        )
        out = args.output_dir / f"newsgroup_tree_{label}.txt"
        out.write_text("\n".join(lines) + "\n", encoding="utf-8")
        print(f"Wrote {out}")


if __name__ == "__main__":
    main()
