import hashlib


def make_hash(string_to_hash: str) -> str:
    return hashlib.blake2b(string_to_hash.encode("utf-8"), digest_size=8).hexdigest()
