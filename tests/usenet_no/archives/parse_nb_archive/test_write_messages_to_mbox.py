"""write_messages_to_mbox decodes a newsgroup's message files into one mbox file.

It appends, since several NB sources can carry the same newsgroup, and reports
what each file was decoded as.
"""

from usenet_no.archives.parse_nb_archive import write_messages_to_mbox


def test_writes_every_message(tmp_path, write_message_file, count_messages):
    message_files = [
        write_message_file(tmp_path / "source" / "001"),
        write_message_file(tmp_path / "source" / "002"),
    ]
    outfile = tmp_path / "no.test.mbox"

    write_messages_to_mbox(message_files, outfile)

    assert count_messages(outfile) == 2


def test_appends_to_an_existing_file(tmp_path, write_message_file, count_messages):
    outfile = tmp_path / "no.test.mbox"

    write_messages_to_mbox([write_message_file(tmp_path / "first" / "001")], outfile)
    write_messages_to_mbox([write_message_file(tmp_path / "second" / "001")], outfile)

    assert count_messages(outfile) == 2


def test_returns_the_encoding_of_each_file(tmp_path, write_message_file):
    """A newsgroup directory can hold messages posted in different encodings."""
    utf8_file = write_message_file(tmp_path / "source" / "001", encoding="utf-8")
    latin1_file = write_message_file(tmp_path / "source" / "002", encoding="latin-1")

    encodings = write_messages_to_mbox(
        [utf8_file, latin1_file], tmp_path / "no.test.mbox"
    )

    assert encodings[utf8_file] == "UTF-8"
    assert encodings[latin1_file] != "UTF-8"


def test_a_from_line_in_a_body_does_not_split_the_message(
    tmp_path, write_message_file, count_messages
):
    """Fails: the source file holds one message, and the body line starting with
    "From " is written unescaped, so the mbox file reads back as two.
    """
    message_file = write_message_file(
        tmp_path / "source" / "001",
        body="Hei\n\nFrom now on I'm thinking only of me.",
    )
    outfile = tmp_path / "no.test.mbox"

    write_messages_to_mbox([message_file], outfile)

    assert count_messages(outfile) == 1


def test_norwegian_characters_survive_the_decode(tmp_path, write_message_file):
    message_file = write_message_file(
        tmp_path / "source" / "001", body="Blåbær", encoding="latin-1"
    )
    outfile = tmp_path / "no.test.mbox"

    write_messages_to_mbox([message_file], outfile)

    assert "Blåbær".encode("utf-8") in outfile.read_bytes()
