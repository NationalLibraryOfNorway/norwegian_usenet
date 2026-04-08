import argparse
from pathlib import Path
import tarfile
import logging
import cchardet as chardet
from usenet_no.mbox_utils import ensure_mbox_envelope

logger = logging.getLogger(__name__)


def extract_tarfiles(zipped_dir: Path, unzipped_dir: Path):
    for compressed_dir in zipped_dir.glob("*.tar"):
        logger.info("Unpacking %s", compressed_dir)
        out_dir = unzipped_dir / compressed_dir.stem
        out_dir.mkdir(parents=True, exist_ok=True)

        logger.info("Extracting %s to %s", compressed_dir, out_dir)

        with tarfile.open(compressed_dir, "r") as tar:
            tar.extractall(path=out_dir)


def find_newsgroups_parent_dir(directory: Path) -> Path:
    """Find the parent directory to all the newsgroups directories"""
    # In one of the directories, the parent dir is named NEWS
    if directory.name == "no" or (
        directory.name == "NEWS" and "KZ" in directory.parent.name
    ):
        return directory
    for e in directory.iterdir():
        if e.is_dir():
            return find_newsgroups_parent_dir(e)


def read_text(text_file: Path) -> str:
    """Read text from a textfile may not be utf-8 encoded"""
    detection = chardet.detect(text_file.read_bytes())
    encoding = detection.get("encoding")
    if encoding in {"VISCII", "EUC-TW", None}:
        logger.debug(
            "Detected encoding %s for file %s. Trying to decode with latin-1",
            encoding,
            text_file,
        )
        logger.debug("bytes: %s", text_file.read_bytes())
        encoding = "latin-1"

    return text_file.read_bytes().decode(encoding, errors="backslashreplace")


def concat_textfiles(newsgroup_dir: Path, outfile: Path) -> None:
    logger.debug("Running concat textfiles in %s (outfile: %s)", newsgroup_dir, outfile)
    files_read = 0
    text = ""
    for each in newsgroup_dir.iterdir():
        if each.is_dir():
            sub_group_outfile = (
                outfile.parent / f"{outfile.stem}.{each.name.lower()}.mbox"
            )
            concat_textfiles(each, outfile=sub_group_outfile)
        else:
            text += ensure_mbox_envelope(read_text(each))
            text += "\n\n"
            files_read += 1

    if files_read:
        with outfile.open("a+") as f:
            f.write(text)

        logger.info("Wrote %d textfiles to %s", files_read, outfile)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Convert NWA tar archives to utf-8 .mbox files"
    )
    parser.add_argument(
        "--zipped-dir",
        type=Path,
        default=Path("data/nwa_90s/zipped_data"),
        help="Directory containing .tar archives",
    )
    parser.add_argument(
        "--unzipped-dir",
        type=Path,
        default=Path("data/nwa_90s/unzipped_data"),
        help="Directory where tar archives are extracted",
    )
    parser.add_argument(
        "--output-directory",
        type=Path,
        default=Path("data/nwa_90s/utf_8_data"),
        help="Directory to write generated .mbox files",
    )

    args = parser.parse_args()
    logger.info("Args: %s", args)

    extract_tarfiles(args.zipped_dir, args.unzipped_dir)

    args.output_directory.mkdir(exist_ok=True, parents=True)

    for directory in args.unzipped_dir.iterdir():
        if not directory.is_dir():
            continue
        logger.info("Finding usenet data in %s", directory)
        newsgroups_parent_dir = find_newsgroups_parent_dir(directory)

        logger.info("Newsgroups parent directory: %s", newsgroups_parent_dir)

        for newsgroup_dir in newsgroups_parent_dir.iterdir():
            if not newsgroup_dir.is_dir():
                continue
            logger.debug("Newsgroup dir: %s", newsgroup_dir)
            outfile = args.output_directory / f"no.{newsgroup_dir.name.lower()}.mbox"
            concat_textfiles(newsgroup_dir=newsgroup_dir, outfile=outfile)
