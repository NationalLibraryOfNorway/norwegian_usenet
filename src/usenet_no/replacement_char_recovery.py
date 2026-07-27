"""Counting how many U+FFFD (�) words in IA can be recovered from the NB vocabulary.

The IA data lost the Norwegian characters æ, ø and å to the Unicode replacement
character U+FFFD. This module measures, without repairing anything, how much of
that loss is recoverable from the NB archive alone.

The idea is a single inverted index keyed on a *masked* word: every æ/ø/å/Æ/Ø/Å
is replaced with U+FFFD, so a correct NB word and its corrupted IA copy collapse
to the same key. Because an IA word already carries U+FFFD where its Norwegian
characters were lost, masking makes the two archives directly comparable.

For each masked key the index holds the set of distinct NB words that produce
it, so a corrupted IA word is:

- *unambiguous* when its key maps to exactly one NB word,
- *ambiguous* when its key maps to several (e.g. ``f�r`` -> ``får``/``før``),
- *unresolvable* when no NB word produces its key.

Only counts leave this module: the words themselves may carry personal
information and are never written out.
"""

import mailbox
from collections import Counter
from collections.abc import Iterable, Iterator
from dataclasses import dataclass
from pathlib import Path

from tqdm import tqdm

from usenet_no.mbox_utils import get_message_body, message_factory
from usenet_no.replacement_chars import NORWEGIAN_CHARS, REPLACEMENT_CHAR

_MASK_TABLE = str.maketrans({char: REPLACEMENT_CHAR for char in NORWEGIAN_CHARS})

UNAMBIGUOUS = "unambiguous"
AMBIGUOUS = "ambiguous"
UNRESOLVABLE = "unresolvable"


@dataclass
class ResolutionCounts:
    """How IA words split across the three recovery outcomes."""

    unambiguous: int
    ambiguous: int
    unresolvable: int


@dataclass
class RecoveryStatistics:
    """Aggregate counts of the recovery experiment, counted two ways.

    ``by_distinct_word`` counts each distinct IA word once; ``by_occurrence``
    weights each by how often it occurs, so it reflects how much of the actual
    corrupted text is recoverable.
    """

    nb_distinct_norwegian_words: int
    nb_distinct_masked_keys: int
    ia_distinct_replacement_words: int
    ia_total_replacement_word_occurrences: int
    by_distinct_word: ResolutionCounts
    by_occurrence: ResolutionCounts


def mask_norwegian_chars(word: str) -> str:
    """Replace every æ/ø/å/Æ/Ø/Å with U+FFFD, leaving existing U+FFFD in place."""
    return word.translate(_MASK_TABLE)


def iter_message_bodies(directory: Path) -> Iterator[str]:
    """Yield every non-empty message body from the .mbox files in a directory."""
    for mbox_file in tqdm(sorted(directory.glob("*.mbox")), unit="file"):
        mbox = mailbox.mbox(str(mbox_file), factory=message_factory)
        for message in mbox:
            body = get_message_body(message)
            if body:
                yield body


def build_norwegian_vocabulary_index(bodies: Iterable[str]) -> dict[str, set[str]]:
    """Map each masked key to the distinct NB words that produce it.

    Only words containing at least one Norwegian character are indexed, because
    only those can be the reconstruction of a U+FFFD word.
    """
    index: dict[str, set[str]] = {}
    for body in bodies:
        for word in body.split():
            if any(char in NORWEGIAN_CHARS for char in word):
                index.setdefault(mask_norwegian_chars(word), set()).add(word)
    return index


def count_replacement_words(bodies: Iterable[str]) -> Counter[str]:
    """Count occurrences of each distinct whitespace token that contains U+FFFD."""
    counts: Counter[str] = Counter()
    for body in bodies:
        for word in body.split():
            if REPLACEMENT_CHAR in word:
                counts[word] += 1
    return counts


def classify_replacement_word(word: str, candidate_counts: dict[str, int]) -> str:
    """Return the recovery outcome of one corrupted word against the NB vocabulary."""
    candidate_count = candidate_counts.get(mask_norwegian_chars(word), 0)
    if candidate_count == 0:
        return UNRESOLVABLE
    if candidate_count == 1:
        return UNAMBIGUOUS
    return AMBIGUOUS


def compute_recovery_statistics(
    vocabulary_index: dict[str, set[str]],
    ia_word_counts: Counter[str],
) -> RecoveryStatistics:
    """Classify every corrupted IA word and aggregate the counts."""
    candidate_counts = {key: len(words) for key, words in vocabulary_index.items()}

    word_categories: Counter[str] = Counter()
    occurrence_categories: Counter[str] = Counter()
    for word, occurrences in ia_word_counts.items():
        category = classify_replacement_word(word, candidate_counts)
        word_categories[category] += 1
        occurrence_categories[category] += occurrences

    return RecoveryStatistics(
        nb_distinct_norwegian_words=sum(
            len(words) for words in vocabulary_index.values()
        ),
        nb_distinct_masked_keys=len(vocabulary_index),
        ia_distinct_replacement_words=len(ia_word_counts),
        ia_total_replacement_word_occurrences=sum(ia_word_counts.values()),
        by_distinct_word=ResolutionCounts(
            unambiguous=word_categories[UNAMBIGUOUS],
            ambiguous=word_categories[AMBIGUOUS],
            unresolvable=word_categories[UNRESOLVABLE],
        ),
        by_occurrence=ResolutionCounts(
            unambiguous=occurrence_categories[UNAMBIGUOUS],
            ambiguous=occurrence_categories[AMBIGUOUS],
            unresolvable=occurrence_categories[UNRESOLVABLE],
        ),
    )
