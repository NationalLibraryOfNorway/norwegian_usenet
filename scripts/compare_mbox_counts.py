"""Compare message counts between new and old utf_8_data directories."""

import argparse
import logging
import mailbox
from pathlib import Path

from usenet_no import _setup_logging

logger = logging.getLogger(__name__)


def compare_dirs(new_dir: Path, old_dir: Path) -> None:
    logger.info("\n=== %s vs %s ===", new_dir, old_dir)
    logger.info(f"{'file':<40} {'old':>8} {'new':>8} {'diff':>8}")
    logger.info("-" * 68)

    all_names = sorted(
        {f.name for f in new_dir.glob("*.mbox")}
        | {f.name for f in old_dir.glob("*.mbox")}
    )

    total_old = total_new = 0
    for name in all_names:
        old_file = old_dir / name
        new_file = new_dir / name
        old_count = len(mailbox.mbox(str(old_file))) if old_file.exists() else None
        new_count = len(mailbox.mbox(str(new_file))) if new_file.exists() else None

        old_str = str(old_count) if old_count is not None else "missing"
        new_str = str(new_count) if new_count is not None else "missing"
        diff = (
            (new_count - old_count)
            if (old_count is not None and new_count is not None)
            else "?"
        )
        diff_str = f"{diff:+d}" if isinstance(diff, int) else diff

        if old_count is not None:
            total_old += old_count
        if new_count is not None:
            total_new += new_count

        logger.info(f"{name:<40} {old_str:>8} {new_str:>8} {diff_str:>8}")

    logger.info("-" * 68)
    logger.info(
        f"{'TOTAL':<40} {total_old:>8} {total_new:>8} {total_new - total_old:>+8}"
    )


if __name__ == "__main__":
    _setup_logging()

    parser = argparse.ArgumentParser(
        description="Compare mbox message counts between new and old utf_8_data dirs"
    )
    parser.add_argument(
        "--ia", action="store_true", help="Compare internet_archive dirs"
    )
    parser.add_argument("--nwa", action="store_true", help="Compare nwa_90s dirs")
    args = parser.parse_args()

    if not args.ia and not args.nwa:
        args.ia = args.nwa = True

    if args.ia:
        compare_dirs(
            Path("data/internet_archive/utf_8_data"),
            Path("data/internet_archive/utf_8_data_old"),
        )
    if args.nwa:
        compare_dirs(
            Path("data/nwa_90s/utf_8_data"),
            Path("data/nwa_90s/utf_8_data_old"),
        )
