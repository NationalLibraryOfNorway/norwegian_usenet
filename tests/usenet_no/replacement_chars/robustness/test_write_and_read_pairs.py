import json

from usenet_no.replacement_chars.robustness import read_pairs, write_pairs


def test_pairs_survive_a_write_and_read(tmp_path, pairs):
    pairs_file = tmp_path / "pairs.jsonl"

    write_pairs(pairs, pairs_file)

    assert read_pairs(pairs_file) == pairs


def test_one_line_per_pair(tmp_path, pairs):
    pairs_file = tmp_path / "pairs.jsonl"

    write_pairs(pairs, pairs_file)

    assert pairs_file.read_text(encoding="utf-8").count("\n") == len(pairs)


def test_norwegian_characters_are_written_as_themselves(tmp_path, make_pair):
    pairs_file = tmp_path / "pairs.jsonl"

    write_pairs([make_pair(0)], pairs_file)

    assert "blåbærsyltetøy" in pairs_file.read_text(encoding="utf-8")


def test_written_lines_hold_every_field(tmp_path, make_pair):
    pairs_file = tmp_path / "pairs.jsonl"

    write_pairs([make_pair(3)], pairs_file)

    assert json.loads(pairs_file.read_text(encoding="utf-8")) == {
        "newsgroup": "no.group.3",
        "message_id_hash": "hash-3",
        "nb_body": "blåbærsyltetøy nummer 3",
        "ia_body": "bl\N{REPLACEMENT CHARACTER}b\N{REPLACEMENT CHARACTER}rsyltet"
        "\N{REPLACEMENT CHARACTER}y nummer 3",
        "replacement_char_count": 3,
    }


def test_no_pairs_write_an_empty_file(tmp_path):
    pairs_file = tmp_path / "pairs.jsonl"

    write_pairs([], pairs_file)

    assert pairs_file.read_text(encoding="utf-8") == ""
    assert read_pairs(pairs_file) == []
