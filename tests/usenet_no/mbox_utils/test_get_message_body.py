"""get_message_body decodes a message's body from its transfer encoding and
charset. A *declared* quoted-printable body is decoded; an *undeclared* one (=XX
escapes with no Content-Transfer-Encoding header) is deliberately left literal
rather than guessed at. These load the raw-IA fixtures and call the decoder in
memory, no parse round-trip."""

import mailbox

from usenet_no.mbox_utils import get_message_body, message_factory


def single_body(mbox_data, filename: str) -> str:
    mbox = mailbox.mbox(str(mbox_data / "ia" / filename), factory=message_factory)
    (key,) = mbox.keys()
    return get_message_body(mbox[key])


def test_undeclared_quoted_printable_is_left_literal(mbox_data):
    """No CTE header means no conversion: the =XX escapes survive unchanged."""
    body = single_body(mbox_data, "no.undeclared.qp.mbox")

    assert body == (
        "Bl=E5b=E6rsyltet=F8y p=E5 loffen. =D8L OG P=D8LSER.\n"
        "Er den =E5 f=E5 kj=F8pe p=E5 bestillingsliste?=20\n"
        "Fetzer zinfandel passer til lam, t=E5ler at lammel=E5ret er =\n"
        "godt krydret.\n"
    )


def test_declared_quoted_printable_iso_8859_1_is_decoded(mbox_data):
    """A declared QP + ISO-8859-1 body decodes to å/ø rather than U+FFFD."""
    body = single_body(mbox_data, "no.declared.qp.mbox")

    assert body == "Vi skal på skiferie. Det blir gøy å gå på ski!\n"
