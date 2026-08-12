"""Shared fixtures for the tests that read sample mbox files.

A newsgroup is derived from the file stem (see
database.extract_messages_from_mbox_file), so each file is named after the case
it demonstrates and that name is what a test asserts on. As in the real
archives, the directory is what separates ia from nb, and the same newsgroup
name can appear in both.
"""

import shutil
from pathlib import Path

import pytest

from usenet_no.database import (
    connect,
    create_schema,
    extract_messages_from_mbox_file,
    insert_messages,
    load_user_ids,
)

DATA_DIR = Path(__file__).parent.parent / "data"


def _load_archives(connection, files_with_archive):
    """Insert every (mbox file, archive) pair into an empty database."""
    user_ids = load_user_ids(connection)
    for mbox_file, archive in files_with_archive:
        insert_messages(
            connection,
            extract_messages_from_mbox_file((mbox_file, archive)),
            user_ids,
        )
    return connection


@pytest.fixture
def mbox_data(tmp_path):
    """The sample archives, copied into tmp_path.

    Copied rather than used in place, because reading an mbox file can leave
    lock files beside it and some functions under test write to their input.
    """
    destination = tmp_path / "data"
    shutil.copytree(DATA_DIR, destination)
    return destination


@pytest.fixture
def database(tmp_path):
    """A connection to an empty database."""
    connection = connect(tmp_path / "test.db")
    create_schema(connection)
    return connection


@pytest.fixture
def load_archives():
    """Load mbox files into a database, as load_archives(database, files_with_archive)."""
    return _load_archives
