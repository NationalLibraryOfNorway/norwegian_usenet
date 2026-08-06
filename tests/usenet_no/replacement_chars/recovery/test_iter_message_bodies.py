"""iter_message_bodies reads the bodies a recovery count is built from.

Given positions, it reads only those, which is how the date span in the database
reaches this module without the mbox files being filtered onto disk.
"""

import pytest

from usenet_no.mbox_utils import RawMessage, write_mbox
from usenet_no.replacement_chars.recovery import iter_message_bodies

BODIES = ["first body", "second body", "", "fourth body"]


@pytest.fixture
def newsgroup_directory(tmp_path):
    """One mbox file of four messages, the third with an empty body."""
    write_mbox(
        [
            RawMessage(envelope=None, text=f"Subject: {index}\n\n{body}\n")
            for index, body in enumerate(BODIES)
        ],
        tmp_path / "no.bodies.mbox",
    )
    return tmp_path


def test_yields_every_non_empty_body(newsgroup_directory):
    assert list(iter_message_bodies(newsgroup_directory)) == [
        "first body",
        "second body",
        "fourth body",
    ]


def test_yields_only_the_bodies_at_the_given_positions(newsgroup_directory):
    bodies = iter_message_bodies(newsgroup_directory, {"no.bodies": [0, 3]})

    assert list(bodies) == ["first body", "fourth body"]


def test_skips_a_file_with_no_positions(newsgroup_directory):
    assert list(iter_message_bodies(newsgroup_directory, {"no.other": [0]})) == []


def test_leaves_out_an_empty_body_at_a_given_position(newsgroup_directory):
    bodies = iter_message_bodies(newsgroup_directory, {"no.bodies": [1, 2]})

    assert list(bodies) == ["second body"]


def test_raises_when_the_file_does_not_hold_the_expected_message_count(
    newsgroup_directory,
):
    """Positions counted against another version of the file would read other messages."""
    bodies = iter_message_bodies(
        newsgroup_directory, {"no.bodies": [0]}, {"no.bodies": 9}
    )

    with pytest.raises(ValueError, match="expected 9"):
        list(bodies)
