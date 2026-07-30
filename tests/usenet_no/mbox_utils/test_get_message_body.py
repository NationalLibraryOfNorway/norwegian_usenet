"""get_message_body decodes a message's body from its transfer encoding and
charset, and returns it whitespace-normalized. A *declared* quoted-printable
body is decoded; an *undeclared* one (=XX escapes with no
Content-Transfer-Encoding header) is deliberately left literal rather than
guessed at. These load the raw-IA fixtures and call the decoder in memory, no
parse round-trip."""

import mailbox

from usenet_no.mbox_utils import get_message_body, message_factory

MULTIPART_MBOX = """\
From sender@example.com
Message-ID: <multipart@example.no>
MIME-Version: 1.0
Content-Type: multipart/mixed; boundary="BOUND"

--BOUND
Content-Type: text/plain; charset="utf-8"

Første del
over to linjer.

--BOUND
Content-Type: text/html; charset="utf-8"

<p>ignorert</p>

--BOUND
Content-Type: text/plain; charset="utf-8"

Andre del.

--BOUND--
"""


def single_body(mbox_data, filename: str) -> str:
    mbox = mailbox.mbox(str(mbox_data / "ia" / filename), factory=message_factory)
    (key,) = mbox.keys()
    return get_message_body(mbox[key])


def test_undeclared_quoted_printable_is_left_literal(mbox_data):
    """No CTE header means no conversion: the =XX escapes survive unchanged."""
    body = single_body(mbox_data, "no.undeclared.qp.mbox")

    assert body == (
        "Bl=E5b=E6rsyltet=F8y p=E5 loffen. =D8L OG P=D8LSER."
        " Er den =E5 f=E5 kj=F8pe p=E5 bestillingsliste?=20"
        " Fetzer zinfandel passer til lam, t=E5ler at lammel=E5ret er ="
        " godt krydret."
    )


def test_declared_quoted_printable_iso_8859_1_is_decoded(mbox_data):
    """A declared QP + ISO-8859-1 body decodes to å/ø rather than U+FFFD."""
    body = single_body(mbox_data, "no.declared.qp.mbox")

    assert body == "Vi skal på skiferie. Det blir gøy å gå på ski!"


def test_body_is_whitespace_normalized(mbox_data):
    """Line breaks and trailing whitespace are collapsed."""
    body = single_body(mbox_data, "no.declared.qp.mbox")

    assert "\n" not in body
    assert body == body.strip()


def test_multipart_joins_text_plain_parts_and_skips_others(tmp_path):
    """The text/plain parts run together as one normalized string; text/html is dropped."""
    mbox_file = tmp_path / "multipart.mbox"
    mbox_file.write_text(MULTIPART_MBOX, encoding="utf-8")
    mbox = mailbox.mbox(str(mbox_file), factory=message_factory)
    (key,) = mbox.keys()

    assert get_message_body(mbox[key]) == "Første del over to linjer. Andre del."
