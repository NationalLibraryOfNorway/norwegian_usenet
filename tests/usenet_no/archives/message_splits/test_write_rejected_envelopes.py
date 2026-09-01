"""The CSV of unescaped "From " lines, one row per line."""

from usenet_no.archives.message_splits import (
    RejectedEnvelope,
    write_rejected_envelopes,
)

REJECTED = [
    RejectedEnvelope("no.general.mbox", 12, [b"From what I hear"]),
    RejectedEnvelope(
        "no.prat.mbox", 40, [b"X-Google-Language: NORWEGIAN", b"Subject: hei"]
    ),
]


def test_writes_a_row_per_line_with_the_header_block_verdict(tmp_path):
    output_file = tmp_path / "counts" / "ia_unescaped_from_lines.csv"

    write_rejected_envelopes(REJECTED, output_file)

    assert output_file.read_text(encoding="utf-8").splitlines() == [
        "source_file,line_number,starts_a_message",
        "no.general.mbox,12,False",
        "no.prat.mbox,40,True",
    ]


def test_leaves_the_line_and_the_lines_under_it_out(tmp_path):
    """The rows name where a line is, and no message text is written out."""
    output_file = tmp_path / "ia_unescaped_from_lines.csv"

    write_rejected_envelopes(REJECTED, output_file)

    assert "From what I hear" not in output_file.read_text(encoding="utf-8")


def test_writes_the_header_row_when_there_is_nothing_to_report(tmp_path):
    output_file = tmp_path / "ia_unescaped_from_lines.csv"

    write_rejected_envelopes([], output_file)

    assert output_file.read_text(encoding="utf-8").splitlines() == [
        "source_file,line_number,starts_a_message"
    ]
