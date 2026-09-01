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

from usenet_no.database import (
    IA_ARCHIVE,
    NB_ARCHIVE,
    connect_archive_and_users,
    connect_archives,
    connect_archives_and_users,
)
from usenet_no.database.build import (
    create_schema,
    extract_messages_from_mbox_file,
    insert_messages,
    load_email_ids,
    load_email_names,
)

DATA_DIR = Path(__file__).parent.parent / "data"


def _build_archive_database(database_file, users_database_file, mbox_files):
    """Load one archive's mbox files into a database and user database of its own."""
    connection = connect_archive_and_users(database_file, users_database_file)
    create_schema(connection)
    email_ids = load_email_ids(connection)
    email_names = load_email_names(connection)
    for mbox_file in mbox_files:
        insert_messages(
            connection,
            extract_messages_from_mbox_file(mbox_file),
            email_ids,
            email_names,
        )
    connection.close()


def _build_archives(tmp_path, files_with_archive):
    """Build the archive and user database of each archive, and return their paths."""
    for archive in (IA_ARCHIVE, NB_ARCHIVE):
        _build_archive_database(
            tmp_path / f"{archive}.db",
            tmp_path / f"{archive}_users.db",
            [
                mbox_file
                for mbox_file, file_archive in files_with_archive
                if file_archive == archive
            ],
        )
    return [
        tmp_path / f"{IA_ARCHIVE}.db",
        tmp_path / f"{NB_ARCHIVE}.db",
        tmp_path / f"{IA_ARCHIVE}_users.db",
        tmp_path / f"{NB_ARCHIVE}_users.db",
    ]


def _load_archives(tmp_path, files_with_archive):
    """Build a database per archive, and open all four files as one connection."""
    return connect_archives_and_users(*_build_archives(tmp_path, files_with_archive))


def _load_public_archives(tmp_path, files_with_archive):
    """Build a database per archive, and open only the two publishable files."""
    return connect_archives(*_build_archives(tmp_path, files_with_archive)[:2])


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
    """A connection to the empty database and user database of a single archive."""
    connection = connect_archive_and_users(
        tmp_path / "test.db", tmp_path / "test_users.db"
    )
    create_schema(connection)
    return connection


@pytest.fixture
def load_archives(tmp_path):
    """Load mbox files into per-archive databases, as load_archives(files_with_archive)."""
    return partial(_load_archives, tmp_path)


@pytest.fixture
def load_public_archives(tmp_path):
    """As load_archives, but without the user databases attached."""
    return partial(_load_public_archives, tmp_path)
