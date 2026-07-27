"""normalize_whitespace collapses whitespace runs; promoted so parsing and the
archive comparison can share one definition. These document its behavior on a
literal and on a real parsed body from the whitespace fixture."""

import mailbox

from usenet_no.mbox_utils import get_message_body, message_factory
from usenet_no.text_normalization import normalize_whitespace


def test_collapses_runs_and_strips_ends():
    assert (
        normalize_whitespace("  Hei og\t\thallo.  \n\n Ola \n") == "Hei og hallo. Ola"
    )


def test_collapses_a_parsed_body(mbox_data):
    mbox = mailbox.mbox(
        str(mbox_data / "ia" / "no.trailing.whitespace.mbox"), factory=message_factory
    )
    (key,) = mbox.keys()
    body = get_message_body(mbox[key])

    assert normalize_whitespace(body) == (
        "Hei og hallo. Dette er en test. Med vennlig hilsen Ola"
    )
