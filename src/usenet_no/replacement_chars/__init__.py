"""Everything that deals with the U+FFFD (�) damage in the IA bodies.

The IA data lost the Norwegian characters æ, ø and å to the Unicode
replacement character U+FFFD. `pairs` reads the mbox files to find the body
conflicts that come down to that loss, and yields the damaged IA body together
with the intact NB body it matches; `recovery` measures how much of the loss
the NB vocabulary can resolve; `robustness` measures how far the loss moves an
embedding model. The vocabulary shared by all three is re-exported here, so
callers import it as `usenet_no.replacement_chars`.
"""

from usenet_no.replacement_chars.pairs import (
    NORWEGIAN_CHARS,
    REPLACEMENT_CHAR,
    NewsgroupReplacementCharCounts,
    ReplacementCharPair,
)

__all__ = [
    "NORWEGIAN_CHARS",
    "REPLACEMENT_CHAR",
    "NewsgroupReplacementCharCounts",
    "ReplacementCharPair",
]
