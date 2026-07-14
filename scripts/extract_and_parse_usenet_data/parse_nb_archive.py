import argparse
import logging
import tarfile
from pathlib import Path

from tqdm import tqdm

from usenet_no.parse_norwegian_web_archive import (
    concat_textfiles,
    find_newsgroups_parent_dir,
)

logger = logging.getLogger(__name__)


def extract_tarfiles(zipped_dir: Path, unzipped_dir: Path):
    for compressed_dir in zipped_dir.glob("*.tar"):
        logger.info("Unpacking %s", compressed_dir)
        out_dir = unzipped_dir / compressed_dir.stem
        out_dir.mkdir(parents=True, exist_ok=True)
        with tarfile.open(compressed_dir, "r") as tar:
            tar.extractall(path=out_dir)
        logger.info("Extracted %s to %s", compressed_dir, out_dir)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Convert NB tar archives to utf-8 .mbox files"
    )
    parser.add_argument(
        "--zipped-dir",
        type=Path,
        default=Path("data/nb/zipped_data"),
        help="Directory containing .tar archives",
    )
    parser.add_argument(
        "--unzipped-dir",
        type=Path,
        default=Path("data/nb/unzipped_data"),
        help="Directory where tar archives are extracted",
    )
    parser.add_argument(
        "--output-directory",
        type=Path,
        default=Path("data/nb/utf_8_data"),
        help="Directory to write generated .mbox files",
    )
    parser.add_argument(
        "--overwrite",
        action="store_true",
        help="Clear output directory and regenerate all mbox files instead of skipping existing",
    )
    args = parser.parse_args()
    logger.info("Args: %s", args)

    extract_tarfiles(args.zipped_dir, args.unzipped_dir)

    args.output_directory.mkdir(exist_ok=True, parents=True)
    if args.overwrite:
        for f in args.output_directory.iterdir():
            f.unlink()
        logger.info("Cleared output directory %s", args.output_directory)

    pre_existing = {f.name for f in args.output_directory.iterdir()}

    directories = [d for d in args.unzipped_dir.iterdir() if d.is_dir()]
    for directory in tqdm(directories, desc="Processing tar archives"):
        logger.info("Finding usenet data in %s", directory)
        newsgroups_parent_dir = find_newsgroups_parent_dir(directory)
        logger.info("Newsgroups parent directory: %s", newsgroups_parent_dir)

        for newsgroup_dir in sorted(newsgroups_parent_dir.iterdir()):
            if not newsgroup_dir.is_dir():
                continue
            outfile = args.output_directory / f"no.{newsgroup_dir.name.lower()}.mbox"
            concat_textfiles(
                newsgroup_dir=newsgroup_dir, outfile=outfile, pre_existing=pre_existing
            )
