"""Find newsgroup name parts that the KZ2001-0147 CD probably cut off.

That CD was written with 8.3 file naming (https://en.wikipedia.org/wiki/8.3_filename), so no directory name on it is longer
than 8 characters. A directory name of exactly 8 characters that the other
three NB sources do not have at the same position in the newsgroup tree, but
that is a true substring of one of their names at that position, was probably
cut off from that longer name.

Extracts the NB tar archives first, when that has not happened yet, since the
detection reads the extracted directory tree. Writes the candidate pairs as a
corrections file, which 02_parse_nb_archive.py reads to merge the cut-off
newsgroups into their full-name mbox files. The file is meant to be reviewed
before use, and can carry hand-added rows for renames this heuristic cannot
find (such as `_` standing in for `-`). Changes nothing in the archive data
itself.
"""

import argparse
import csv
import logging
from pathlib import Path

from usenet_no.parse_norwegian_web_archive import (
    extract_tarfiles,
    find_newsgroups_parent_dir,
)

logger = logging.getLogger(__name__)

LIMITED_SOURCE = "KZ2001-0147"

# The KZ2001-0147 CD was written with 8.3 file naming, so no directory name on
# it is longer than 8 characters: longer newsgroup name parts were cut off.
CD_NAME_LENGTH_LIMIT = 8

DirectoryPath = tuple[str, ...]


def collect_directory_paths(root: Path) -> set[DirectoryPath]:
    """Collect the path of every directory below root, as lowercased name parts.

    Newsgroup names are built from these directory names (see
    parse_norwegian_web_archive.concat_textfiles), and lowercased there too, so
    lowercasing here lets names from the uppercase-only KZ2001-0147 CD be
    compared with the other sources'.
    """
    return {
        tuple(part.lower() for part in directory.relative_to(root).parts)
        for directory in root.rglob("*")
        if directory.is_dir()
    }


def find_cut_off_candidates(
    limited_paths: set[DirectoryPath], full_paths: set[DirectoryPath]
) -> list[tuple[DirectoryPath, DirectoryPath]]:
    """Pair each path that was probably cut off with the full paths it may be.

    A path from the length-limited source is a cut-off candidate when its last
    name part is exactly CD_NAME_LENGTH_LIMIT characters long and the path does
    not itself appear in the other sources: a path the other sources also have
    was most likely always that short. Each candidate is paired with every path
    from the other sources that has the same parent path and whose last part
    the candidate's last part is a true substring of.

    Returned sorted by (candidate, full path) so reruns produce identical output.
    """
    return [
        (path, full_path)
        for path in sorted(limited_paths)
        if len(path[-1]) == CD_NAME_LENGTH_LIMIT and path not in full_paths
        for full_path in sorted(full_paths)
        if full_path[:-1] == path[:-1] and path[-1] in full_path[-1]
    ]


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description=f"Print newsgroup directory names from {LIMITED_SOURCE} that were probably cut off, next to the full names they may be"
    )
    parser.add_argument(
        "--zipped-dir",
        type=Path,
        default=Path("data/nb/zipped_data"),
        help="Directory containing the NB .tar archives",
    )
    parser.add_argument(
        "--unzipped-dir",
        type=Path,
        default=Path("data/nb/unzipped_data"),
        help="Directory where tar archives are extracted",
    )
    parser.add_argument(
        "--output-file",
        type=Path,
        default=Path("data/cut_off_newsgroup_names.csv"),
        help="CSV file to write the corrections to",
    )
    parser.add_argument(
        "--overwrite",
        action="store_true",
        help="If flagged, will overwrite an existing corrections file (discarding any hand-added rows)",
    )

    args = parser.parse_args()
    logging.basicConfig(level=logging.INFO)
    logger.info("Args: %s", args)

    if args.output_file.exists() and not args.overwrite:
        logger.info(
            "Corrections file already exists: %s. Use --overwrite to regenerate.",
            args.output_file,
        )
        exit(0)

    extract_tarfiles(args.zipped_dir, args.unzipped_dir)

    limited_paths: set[DirectoryPath] = set()
    full_paths: set[DirectoryPath] = set()
    for source_dir in sorted(args.unzipped_dir.iterdir()):
        if not source_dir.is_dir():
            continue
        newsgroups_dir = find_newsgroups_parent_dir(source_dir)
        paths = collect_directory_paths(newsgroups_dir)
        if LIMITED_SOURCE in newsgroups_dir.parts:
            limited_paths |= paths
        else:
            full_paths |= paths
        logger.info("%s: %d directories", source_dir.name, len(paths))

    candidates = find_cut_off_candidates(limited_paths, full_paths)
    # Written as full newsgroup mbox file stems, which is what
    # 02_parse_nb_archive.py builds output filenames from
    with args.output_file.open("w", encoding="utf-8", newline="") as file:
        writer = csv.writer(file)
        writer.writerow(["cut_off_name", "full_name"])
        for path, full_path in candidates:
            writer.writerow([f"no.{'.'.join(path)}", f"no.{'.'.join(full_path)}"])
            print(f"no.{'.'.join(path)} -> no.{'.'.join(full_path)}")
    logger.info(
        "Wrote %d cut-off candidate pairs to %s", len(candidates), args.output_file
    )
