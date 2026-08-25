"""
Writes a text file listing the original newsgroup
hierarchy, found on the original NB CDs,
similar to how `tree` would do in a terminal.
"""

from pathlib import Path

ORIGINAL_DATA_DIR = Path("data/input/nb/unzipped_data")
OUTPUT_DIR = Path("data/output/01_extract_and_parse_usenet_data")


def iter_directory_tree(root, prefix=""):
    """
    Takes a directory as input,
    returns each sub-directory as a line in tree-style
    """
    subdirs = sorted(d for d in root.iterdir() if d.is_dir())
    for index, subdir in enumerate(subdirs):
        is_last = index == len(subdirs) - 1
        yield f"{prefix}{'└── ' if is_last else '├── '}{subdir.name}"
        yield from iter_directory_tree(subdir, prefix + ("    " if is_last else "│   "))


OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

for source_dir in sorted(ORIGINAL_DATA_DIR.glob("*")):
    if not source_dir.is_dir():
        continue
    tree = list(iter_directory_tree(source_dir))
    outfile = OUTPUT_DIR / f"{source_dir.name}-original-hierarchy.txt"
    outfile.write_text(
        "\n".join([source_dir.name, *tree, "", f"{len(tree)} directories"]) + "\n",
        encoding="utf-8",
    )
    print(f"Wrote {outfile} ({len(tree)} directories)")