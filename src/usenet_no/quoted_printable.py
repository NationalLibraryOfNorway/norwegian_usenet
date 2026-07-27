"""Detecting undeclared quoted-printable bodies in the IA archive.

Some IA messages carry a quoted-printable body (=E5 for å, =F8 for ø, ...)
without a Content-Transfer-Encoding header to declare it, so the email library
never reverses it and the =XX escapes survive. Such a body is pure ASCII apart
from the escapes.

Detection keys on the Norwegian letters æ Æ ø Ø å Å specifically, the characters
this archive lost to quoted-printable. Matching only those (rather than any =XX
for a byte >= 0x80) keeps URL query strings such as ?q=cache (=ca) or
?id=9092335 (=90) from looking like QP. Once a body is recognised, quopri still
reverses every escape it carries, not just the Norwegian ones. The body decoder
in `usenet_no.mbox_utils` and the statistics script that counts affected
messages share this one definition.
"""

import re
from mailbox import mboxMessage

# Quoted-printable escapes for the Norwegian letters å/Å, æ/Æ, ø/Ø, whose bytes
# are E5/C5, E6/C6, F8/D8 in ISO-8859-1, Windows-1252 and ISO-8859-15 alike.
# Case-insensitive because some encoders emit lower-case hex (=e5).
NORWEGIAN_QP_ESCAPE = re.compile(rb"=(?:c5|c6|d8|e5|e6|f8)", re.IGNORECASE)
# Transfer encodings that leave the body bytes unchanged, so an undeclared QP
# body reaches us unreversed. A declared quoted-printable/base64 is reversed by
# the email library before we ever see the payload.
IDENTITY_TRANSFER_ENCODINGS = {None, "7bit", "8bit", "binary"}


def count_norwegian_escapes(payload: bytes) -> int:
    """Number of quoted-printable escapes for a Norwegian letter (æøåÆØÅ)."""
    return len(NORWEGIAN_QP_ESCAPE.findall(payload))


def is_undeclared_quoted_printable(
    payload: bytes, transfer_encoding: str | None, min_escapes: int = 1
) -> bool:
    """True when body bytes look like undeclared quoted-printable.

    `transfer_encoding` is the lower-cased Content-Transfer-Encoding value, or
    None. The body must declare no real transfer encoding, be pure ASCII, and
    carry at least `min_escapes` quoted-printable escapes for a Norwegian letter.
    """
    return (
        transfer_encoding in IDENTITY_TRANSFER_ENCODINGS
        and payload.isascii()
        and count_norwegian_escapes(payload) >= min_escapes
    )


def message_is_undeclared_quoted_printable(
    message: mboxMessage, min_escapes: int = 1
) -> bool:
    """True when any text/plain part of a message is undeclared quoted-printable."""
    parts = message.walk() if message.is_multipart() else [message]
    for part in parts:
        if message.is_multipart() and part.get_content_type() != "text/plain":
            continue
        payload = part.get_payload(decode=True)
        if not payload:
            continue
        transfer_encoding = part.get("Content-Transfer-Encoding")
        transfer_encoding = transfer_encoding.lower() if transfer_encoding else None
        if is_undeclared_quoted_printable(payload, transfer_encoding, min_escapes):
            return True
    return False
