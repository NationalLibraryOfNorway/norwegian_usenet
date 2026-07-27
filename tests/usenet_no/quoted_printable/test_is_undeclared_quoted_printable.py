"""The undeclared-quoted-printable predicate shared by the body decoder and the
statistics script: identity transfer encoding, pure ASCII, and enough
quoted-printable escapes for a Norwegian letter (æøåÆØÅ)."""

from email import policy
from email.parser import BytesParser

from usenet_no.quoted_printable import (
    count_norwegian_escapes,
    is_undeclared_quoted_printable,
    message_is_undeclared_quoted_printable,
)


def _message(raw: bytes):
    return BytesParser(policy=policy.default.clone(utf8=True)).parsebytes(raw)


def test_counts_only_norwegian_escapes():
    # =E5/=E6 are å/æ; =CA (non-Norwegian), =20, =42 and "===" are not counted.
    assert count_norwegian_escapes(b"Bl=E5b=E6r p=E5? =CA =20 total=42 ===") == 3


def test_undeclared_norwegian_escapes_are_quoted_printable():
    assert is_undeclared_quoted_printable(b"Bl=E5b=E6r", transfer_encoding=None)


def test_lowercase_hex_escape_is_matched():
    assert is_undeclared_quoted_printable(b"selvf=f8lgelig", transfer_encoding=None)


def test_non_norwegian_high_byte_escapes_are_not_quoted_printable():
    # URL query strings carry =XX-looking bytes that are not Norwegian letters.
    assert not is_undeclared_quoted_printable(b"?q=cache", transfer_encoding=None)
    assert not is_undeclared_quoted_printable(b"?did=9092335", transfer_encoding=None)


def test_declared_quoted_printable_is_not_undeclared():
    # A declared transfer encoding is reversed by the email library, not here.
    assert not is_undeclared_quoted_printable(
        b"Bl=E5b=E6r", transfer_encoding="quoted-printable"
    )


def test_non_ascii_body_is_not_undeclared_quoted_printable():
    # A UTF-8 body with a stray escape must be left alone.
    assert not is_undeclared_quoted_printable(
        "Sæther =E5".encode("utf-8"), transfer_encoding=None
    )


def test_min_escapes_threshold_excludes_single_escape():
    assert is_undeclared_quoted_printable(b"Bl=E5b=E6r", None, min_escapes=2)
    assert not is_undeclared_quoted_printable(b"G=F8y!", None, min_escapes=2)


def test_message_predicate_reads_transfer_encoding_header():
    undeclared = _message(b"Message-ID: <a@no>\n\nBl=E5b=E6r p=E5 loffen.\n")
    declared = _message(
        b"Content-Transfer-Encoding: quoted-printable\n\nBl=E5b=E6r p=E5 loffen.\n"
    )

    assert message_is_undeclared_quoted_printable(undeclared)
    assert not message_is_undeclared_quoted_printable(declared)
