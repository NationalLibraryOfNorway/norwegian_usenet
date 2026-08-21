"""Shared fixtures for the tests that read sample mbox files.

A newsgroup is derived from the file stem (see
database.build.extract_messages_from_mbox_file), so each file is named after the case
it demonstrates and that name is what a test asserts on. As in the real
archives, the directory is what separates ia from nb, and the same newsgroup
name can appear in both.
"""

import shutil
from functools import partial
from pathlib import Path

import pytest

from usenet_no.database import IA_ARCHIVE, NB_ARCHIVE, connect, connect_archives
from usenet_no.database.build import (
    create_schema,
    extract_messages_from_mbox_file,
    insert_messages,
    load_user_ids,
)

DATA_DIR = Path(__file__).parent.parent / "data"


def _build_archive_database(database_file, mbox_files):
    """Load one archive's mbox files into a database of its own."""
    connection = connect(database_file)
    create_schema(connection)
    user_ids = load_user_ids(connection)
    for mbox_file in mbox_files:
        insert_messages(
            connection, extract_messages_from_mbox_file(mbox_file), user_ids
        )
    connection.close()


def _load_archives(tmp_path, files_with_archive):
    """Build a database per archive, and open the two of them as one connection."""
    for archive in (IA_ARCHIVE, NB_ARCHIVE):
        _build_archive_database(
            tmp_path / f"{archive}.db",
            [
                mbox_file
                for mbox_file, file_archive in files_with_archive
                if file_archive == archive
            ],
        )
    return connect_archives(
        tmp_path / f"{IA_ARCHIVE}.db", tmp_path / f"{NB_ARCHIVE}.db"
    )


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
    """A connection to an empty database of a single archive."""
    connection = connect(tmp_path / "test.db")
    create_schema(connection)
    return connection


@pytest.fixture
def load_archives(tmp_path):
    """Load mbox files into per-archive databases, as load_archives(files_with_archive)."""
    return partial(_load_archives, tmp_path)
