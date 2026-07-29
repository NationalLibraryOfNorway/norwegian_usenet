"""Whitespace normalization shared by the archive comparison and, in future, parsing.

Promoted out of `usenet_no.replacement_chars.pairs` so that the normalization
applied when comparing bodies and the normalization applied when parsing an
archive can be the same function rather than two definitions that might drift.
"""


def normalize_whitespace(text: str) -> str:
    """Collapse every run of whitespace to a single space and strip the ends.

    Folds away the differences that come from the two archives reflowing or
    re-wrapping the same text: trailing spaces, CRLF vs LF, blank-line runs.
    """
    return " ".join(text.split())
