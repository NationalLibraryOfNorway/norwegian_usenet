"""_normalize_whitespace collapses whitespace runs. These document its behavior
on a literal and on a real parsed body from the whitespace fixture."""

import mailbox

from usenet_no.mbox_utils import (
    _normalize_whitespace,
    get_message_body,
    message_factory,
)


def test_collapses_runs_and_strips_ends():
    assert (
        _normalize_whitespace("  Hei og\t\thallo.  \n\n Ola \n") == "Hei og hallo. Ola"
    )


def test_a_parsed_body_arrives_collapsed(mbox_data):
    mbox = mailbox.mbox(
        str(mbox_data / "ia" / "no.trailing.whitespace.mbox"), factory=message_factory
    )
    (key,) = mbox.keys()

    assert get_message_body(mbox[key]) == (
        "Hei og hallo. Dette er en test. Med vennlig hilsen Ola"
    )
