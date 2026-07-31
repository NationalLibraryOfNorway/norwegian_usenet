"""Plot message-id overlap and reference coverage between IA and NB."""

import argparse
import json
from pathlib import Path

import matplotlib.pyplot as plt

from usenet_no.plot_utils import venn2_fmt


def load(path: Path) -> dict:
    with open(path) as f:
        return json.load(f)


def fmt(n: int) -> str:
    return f"{n:,}".replace(",", " ")


def plot_id_overlap_venn(filtered: dict, full: dict, out_path: Path) -> None:
    fig, axes = plt.subplots(1, 2, figsize=(12, 5))
    for ax, data, title in [
        (axes[0], filtered, "1994-1997"),
        (axes[1], full, "full period"),
    ]:
        venn2_fmt(
            subsets=(data["ids_nb_only"], data["ids_ia_only"], data["ids_in_both"]),
            set_labels=("NB", "IA"),
            ax=ax,
            show_pct=True,
        )
        ax.set_title(f"Message ID overlap ({title})")
    fig.tight_layout()
    fig.savefig(out_path)
    plt.close(fig)


def print_reference_resolution(dfs: list) -> None:
    for label, data in dfs:
        ia_resolved = data["ia_refs_resolved_by_nb"]
        ia_total = (
            ia_resolved + data["ghost_cited_by_ia_only"] + data["ghost_cited_by_both"]
        )
        nb_resolved = data["nb_refs_resolved_by_ia"]
        nb_total = (
            nb_resolved + data["ghost_cited_by_nb_only"] + data["ghost_cited_by_both"]
        )
        print(f"{label}:")
        print(
            f"  IA refs resolved by NB:  {fmt(ia_resolved)} of {fmt(ia_total)} ({ia_resolved / ia_total:.2%})"
        )
        print(
            f"  NB refs resolved by IA:   {fmt(nb_resolved)} of {fmt(nb_total)} ({nb_resolved / nb_total:.2%})"
        )
        print()


def plot_outside_references_venn(data: dict, out_path: Path) -> None:
    ghost_ia = data["ghost_cited_by_ia_only"] + data["ghost_cited_by_both"]
    ghost_nb = data["ghost_cited_by_nb_only"] + data["ghost_cited_by_both"]

    fig, axes = plt.subplots(1, 2, figsize=(13, 5))
    for ax, (archive, ghost, resolved, other) in zip(
        axes,
        [
            ("NB", ghost_nb, data["nb_refs_resolved_by_ia"], "IA"),
            ("IA", ghost_ia, data["ia_refs_resolved_by_nb"], "NB"),
        ],
    ):
        venn2_fmt(
            subsets=(ghost, 0, resolved),
            set_labels=("", f"References resolved by {other}"),
            ax=ax,
            show_pct=True,
        )
        ax.set_title(f"References to messages outside {archive} data")
    fig.tight_layout()
    fig.savefig(out_path)
    plt.close(fig)


def print_ghost_references(dfs: list) -> None:
    for label, data in dfs:
        print(f"{label}:")
        print(f"  Cited by IA only:  {fmt(data['ghost_cited_by_ia_only'])}")
        print(f"  Cited by NB only: {fmt(data['ghost_cited_by_nb_only'])}")
        print(f"  Cited by both:     {fmt(data['ghost_cited_by_both'])}")
        print()


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Plot message-id overlap and reference coverage between IA and NB"
    )
    parser.add_argument(
        "--overlap-json",
        type=Path,
        default=Path("data/output/04_compare_archives/ia_nb_message_id_overlap.json"),
        help="JSON with message-id overlap counts (default: %(default)s)",
    )
    parser.add_argument(
        "--overlap-date-filtered-json",
        type=Path,
        default=Path(
            "data/output/04_compare_archives/ia_nb_message_id_overlap_date_filtered.json"
        ),
        help="JSON with date filtered message-id overlap counts (default: %(default)s)",
    )
    parser.add_argument(
        "--out-dir",
        type=Path,
        default=Path("data/output/08_visualize/plot_ia_nb_message_id_overlap"),
        help="Directory for output .png files (default: %(default)s)",
    )
    args = parser.parse_args()
    args.out_dir.mkdir(parents=True, exist_ok=True)

    full = load(args.overlap_json)
    filtered = load(args.overlap_date_filtered_json)
    dfs = [("Full IA", full), ("IA date-filtered", filtered)]

    plot_id_overlap_venn(filtered, full, args.out_dir / "message_id_overlap_venn.png")
    print_reference_resolution(dfs)
    plot_outside_references_venn(
        filtered, args.out_dir / "outside_archive_references_venn.png"
    )
    print_ghost_references(dfs)


if __name__ == "__main__":
    main()
