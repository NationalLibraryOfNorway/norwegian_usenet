import pytest

from usenet_no.mbox_utils import get_message_bodies_at_positions

DUMMY_MBOX = """\
From sender@example.com
Message-ID: <first@example.no>

first body

From sender@example.com
Message-ID: <second@example.no>

second body

From sender@example.com
Message-ID: <third@example.no>

third body
"""


@pytest.fixture
def mbox_file(tmp_path):
    mbox_file = tmp_path / "test.mbox"
    mbox_file.write_text(DUMMY_MBOX)
    return mbox_file


def test_returns_bodies_by_position(mbox_file):
    bodies = get_message_bodies_at_positions(mbox_file, [2, 0])

    assert bodies == {0: "first body", 2: "third body"}


def test_accepts_matching_expected_message_count(mbox_file):
    bodies = get_message_bodies_at_positions(mbox_file, [1], expected_message_count=3)

    assert bodies == {1: "second body"}


def test_raises_on_wrong_expected_message_count(mbox_file):
    with pytest.raises(ValueError, match="expected 5"):
        get_message_bodies_at_positions(mbox_file, [1], expected_message_count=5)


def test_raises_on_position_beyond_the_file(mbox_file):
    with pytest.raises(ValueError, match="no message at positions"):
        get_message_bodies_at_positions(mbox_file, [3])
