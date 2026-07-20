from usenet_no.database import (
    IA_ARCHIVE,
    NB_ARCHIVE,
    connect,
    create_schema,
    extract_messages_from_mbox_file,
    insert_messages,
    load_user_ids,
)
from usenet_no.mbox_utils import write_mbox
from usenet_no.statistics import (
    count_messages_per_date,
    count_messages_per_group,
    count_messages_per_user,
    count_messages_without_sender,
    get_date_span,
)


def _make_mbox(path, messages):
    texts = []
    for message in messages:
        headers = "".join(
            f"{header}: {value}\n"
            for header, value in message.items()
            if header != "body"
        )
        texts.append(f"From sender@example.com\n{headers}\n{message['body']}\n")
    write_mbox(texts, path)


def _database_with(tmp_path, files_with_archive):
    connection = connect(tmp_path / "test.db")
    create_schema(connection)
    user_ids = load_user_ids(connection)
    for mbox_file, archive in files_with_archive:
        insert_messages(
            connection, extract_messages_from_mbox_file((mbox_file, archive)), user_ids
        )
    return connection


def _date(day):
    return f"Mon, {day} Jan 1996 12:00:00 +0000"


def test_counts_messages_per_newsgroup_of_one_archive(tmp_path):
    first = tmp_path / "no.first.mbox"
    second = tmp_path / "no.second.mbox"
    other_archive = tmp_path / "no.third.mbox"
    _make_mbox(first, [{"body": "a"}, {"body": "b"}])
    _make_mbox(second, [{"body": "c"}])
    _make_mbox(other_archive, [{"body": "d"}])
    connection = _database_with(
        tmp_path,
        [(first, IA_ARCHIVE), (second, IA_ARCHIVE), (other_archive, NB_ARCHIVE)],
    )

    assert count_messages_per_group(connection, IA_ARCHIVE) == {
        "no.first": 2,
        "no.second": 1,
    }


def test_date_span_ignores_unparseable_dates(tmp_path):
    mbox_file = tmp_path / "no.test.mbox"
    _make_mbox(
        mbox_file,
        [
            {"Date": _date("06"), "body": "a"},
            {"Date": "nonsense", "body": "b"},
            {"Date": _date("20"), "body": "c"},
        ],
    )
    connection = _database_with(tmp_path, [(mbox_file, NB_ARCHIVE)])

    assert get_date_span(connection, NB_ARCHIVE) == ("1996-01-06", "1996-01-20")


def test_date_filtering_excludes_messages_outside_the_span(tmp_path):
    mbox_file = tmp_path / "no.test.mbox"
    _make_mbox(
        mbox_file,
        [
            {"Date": "Mon, 01 Jan 1990 12:00:00 +0000", "body": "too early"},
            {"Date": _date("10"), "body": "inside"},
            {"Date": "Mon, 01 Jan 2005 12:00:00 +0000", "body": "too late"},
        ],
    )
    connection = _database_with(tmp_path, [(mbox_file, IA_ARCHIVE)])

    counts = count_messages_per_group(
        connection, IA_ARCHIVE, date_span=("1996-01-06", "1996-01-20")
    )

    assert counts == {"no.test": 1}


def test_date_filtering_keeps_messages_with_unparseable_dates(tmp_path):
    """Matches how the date-filtered archive was built: only drop known misses."""
    mbox_file = tmp_path / "no.test.mbox"
    _make_mbox(
        mbox_file,
        [
            {"Date": "nonsense", "body": "unknown date"},
            {"Date": _date("10"), "body": "inside"},
            {"Date": "Mon, 01 Jan 2005 12:00:00 +0000", "body": "too late"},
        ],
    )
    connection = _database_with(tmp_path, [(mbox_file, IA_ARCHIVE)])

    counts = count_messages_per_group(
        connection, IA_ARCHIVE, date_span=("1996-01-06", "1996-01-20")
    )

    assert counts == {"no.test": 2}


def test_counts_are_sorted_by_newsgroup(tmp_path):
    files = []
    for name in ["no.zebra", "no.alpha", "no.middle"]:
        mbox_file = tmp_path / f"{name}.mbox"
        _make_mbox(mbox_file, [{"body": "x"}])
        files.append((mbox_file, IA_ARCHIVE))
    connection = _database_with(tmp_path, files)

    counts = count_messages_per_group(connection, IA_ARCHIVE)

    assert list(counts) == ["no.alpha", "no.middle", "no.zebra"]


def test_counts_messages_with_no_from_header(tmp_path):
    """A message with no From header has no user, and is counted here."""
    with_sender = tmp_path / "no.withsender.mbox"
    _make_mbox(with_sender, [{"From": "a@b.no", "body": "known"}])
    # Written directly, since _make_mbox always supplies a From header
    without_sender = tmp_path / "no.nosender.mbox"
    without_sender.write_text(
        "From \nSubject: one\n\nbody one\n\nFrom \nSubject: two\n\nbody two\n\n"
    )
    connection = _database_with(
        tmp_path, [(with_sender, IA_ARCHIVE), (without_sender, IA_ARCHIVE)]
    )

    assert count_messages_without_sender(connection) == [("ia", "no.nosender", 2)]


def test_no_rows_when_every_message_has_a_sender(tmp_path):
    mbox_file = tmp_path / "no.test.mbox"
    _make_mbox(mbox_file, [{"From": "a@b.no", "body": "known"}])
    connection = _database_with(tmp_path, [(mbox_file, IA_ARCHIVE)])

    assert count_messages_without_sender(connection) == []


def test_counts_messages_per_user_by_hash(tmp_path):
    mbox_file = tmp_path / "no.test.mbox"
    _make_mbox(
        mbox_file,
        [
            {"From": "Tita <t@x.no>", "body": "one"},
            {"From": "Tita <t@x.no>", "body": "two"},
            {"From": "Ola <o@x.no>", "body": "three"},
        ],
    )
    connection = _database_with(tmp_path, [(mbox_file, IA_ARCHIVE)])

    counts = count_messages_per_user(connection, IA_ARCHIVE)

    assert sorted(count for _n, _e, count in counts) == [1, 2]
    # Only hashes are returned, never the address itself
    assert all("@" not in (email or "") for _n, email, _c in counts)


def test_per_user_counts_exclude_messages_without_sender(tmp_path):
    with_sender = tmp_path / "no.a.mbox"
    _make_mbox(with_sender, [{"From": "a@b.no", "body": "known"}])
    without_sender = tmp_path / "no.b.mbox"
    without_sender.write_text("From \nSubject: x\n\nbody\n\n")
    connection = _database_with(
        tmp_path, [(with_sender, IA_ARCHIVE), (without_sender, IA_ARCHIVE)]
    )

    counts = count_messages_per_user(connection, IA_ARCHIVE)

    assert len(counts) == 1


def test_per_user_counts_respect_the_date_span(tmp_path):
    mbox_file = tmp_path / "no.test.mbox"
    _make_mbox(
        mbox_file,
        [
            {"From": "a@b.no", "Date": _date("10"), "body": "inside"},
            {
                "From": "c@d.no",
                "Date": "Mon, 01 Jan 2005 12:00:00 +0000",
                "body": "out",
            },
        ],
    )
    connection = _database_with(tmp_path, [(mbox_file, IA_ARCHIVE)])

    counts = count_messages_per_user(
        connection, IA_ARCHIVE, date_span=("1996-01-06", "1996-01-20")
    )

    assert len(counts) == 1


def test_counts_messages_per_date_with_undated_last(tmp_path):
    mbox_file = tmp_path / "no.test.mbox"
    _make_mbox(
        mbox_file,
        [
            {"Date": _date("20"), "body": "later"},
            {"Date": _date("06"), "body": "earlier"},
            {"Date": "nonsense", "body": "undated"},
        ],
    )
    connection = _database_with(tmp_path, [(mbox_file, NB_ARCHIVE)])

    counts = count_messages_per_date(connection, NB_ARCHIVE)

    # Sorted by date, with the undated group last so it lands at the CSV's end
    assert counts == [("1996-01-06", 1), ("1996-01-20", 1), (None, 1)]
