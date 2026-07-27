"""get_message_body is where a message's body is actually decoded (payload
transfer-encoding + charset), and where the IA quoted-printable damage shows up.

These load the raw-IA fixtures directly and call the decoder in memory, no parse
round-trip. They assert the desired quoted-printable decoding and so FAIL until
the body-decode fix lands; the current output is literal =XX (undeclared QP) or
U+FFFD (declared QP + ISO-8859-1). The expected strings are the QP-decoded body
only, before any whitespace normalization, to keep this about decoding.
"""

import mailbox

from usenet_no.mbox_utils import get_message_body, message_factory


def single_body(mbox_data, filename: str) -> str:
    mbox = mailbox.mbox(str(mbox_data / "ia" / filename), factory=message_factory)
    (key,) = mbox.keys()
    return get_message_body(mbox[key])


def test_undeclared_quoted_printable_is_decoded(mbox_data):
    """Without a CTE header the QP is still resolved: =E5/=E6/=F8/=D8 -> å/æ/ø/Ø,
    =20 -> space, and the trailing "=" joins its line."""
    body = single_body(mbox_data, "no.undeclared.qp.mbox")

    assert body == (
        "Blåbærsyltetøy på loffen. ØL OG PØLSER.\n"
        "Er den å få kjøpe på bestillingsliste? \n"
        "Fetzer zinfandel passer til lam, tåler at lammelåret er godt krydret.\n"
    )


def test_declared_quoted_printable_iso_8859_1_is_decoded(mbox_data):
    """A declared QP + ISO-8859-1 body decodes to å/ø rather than U+FFFD."""
    body = single_body(mbox_data, "no.declared.qp.mbox")

    assert body == "Vi skal på skiferie. Det blir gøy og går på ski!\n"
