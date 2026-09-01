"""connect_archives_and_users attaches the user databases connect_archives leaves out."""

import sqlite3

import pytest

from usenet_no.database import IA_ARCHIVE


def test_public_connection_cannot_read_a_hashed_address(
    mbox_data, load_public_archives
):
    """The archive databases carry a sender as an email id and nothing else, so
    the hashed address is out of reach without the user databases attached."""
    connection = load_public_archives(
        [(mbox_data / "ia/no.full.message.mbox", IA_ARCHIVE)]
    )

    with pytest.raises(sqlite3.OperationalError):
        connection.execute("SELECT email_hash FROM emails").fetchall()


def test_attaching_the_user_databases_brings_the_addresses_back(
    mbox_data, load_archives
):
    connection = load_archives([(mbox_data / "ia/no.full.message.mbox", IA_ARCHIVE)])

    archives = {
        archive for (archive,) in connection.execute("SELECT archive FROM emails")
    }

    assert archives == {IA_ARCHIVE}
