"""Pairs built by hand, since the robustness functions only see body text.

The bodies here are stand-ins: what the functions under test do with a pair
does not depend on it being a real damaged/intact body, only on the two texts
belonging together.
"""

import pytest

from usenet_no.replacement_chars import REPLACEMENT_CHAR, ReplacementCharPair
from usenet_no.replacement_chars.robustness import PairSimilarity


def _make_pair(
    index: int, newsgroup: str | None = None, message_id_hash: str | None = None
) -> ReplacementCharPair:
    """A pair whose fields all carry the index, so a sample can be traced back.

    The newsgroup and the message id can be set apart from the index, for the
    tests about crossposting (one id in several newsgroups) and about balance
    (several ids in one newsgroup).
    """
    return ReplacementCharPair(
        newsgroup=f"no.group.{index}" if newsgroup is None else newsgroup,
        message_id_hash=f"hash-{index}" if message_id_hash is None else message_id_hash,
        nb_body=f"blåbærsyltetøy nummer {index}",
        ia_body=f"bl{REPLACEMENT_CHAR}b{REPLACEMENT_CHAR}rsyltet{REPLACEMENT_CHAR}y"
        f" nummer {index}",
        replacement_char_count=3,
    )


def _make_similarity(index: int, matched_similarity: float) -> PairSimilarity:
    """The scored row of the pair with the same index, from `_make_pair`."""
    return PairSimilarity(
        newsgroup=f"no.group.{index}",
        message_id_hash=f"hash-{index}",
        replacement_char_count=3,
        nb_body_length=23,
        matched_similarity=matched_similarity,
        shuffled_similarity=0.2,
    )


@pytest.fixture
def make_pair():
    return _make_pair


@pytest.fixture
def make_similarity():
    return _make_similarity


@pytest.fixture
def pairs():
    """Twenty pairs, each its own message id in its own newsgroup."""
    return [_make_pair(index) for index in range(20)]
