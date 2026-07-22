import hashlib
from pathlib import Path

import pandas as pd


def make_hash(string_to_hash: str) -> str:
    return hashlib.blake2b(string_to_hash.encode("utf-8"), digest_size=8).hexdigest()


def get_hash_dict(file: Path) -> dict[str, str]:
    return dict(
        pd.read_csv(file, keep_default_na=False).itertuples(index=False, name=None)
    )
