"""The CSV both header field counting scripts write."""

import csv

from usenet_no.archives.header_fields import (
    HeaderFieldCounts,
    write_header_field_counts,
)


def read_rows(output_file):
    with output_file.open(encoding="utf-8", newline="") as file:
        return list(csv.reader(file))


def test_writes_one_row_per_field_with_its_share_of_the_messages(tmp_path):
    output_file = tmp_path / "header_field_counts.csv"
    counts = HeaderFieldCounts(message_count=4, field_counts={"From": 4, "Subject": 1})

    write_header_field_counts(counts, output_file)

    assert read_rows(output_file) == [
        ["field", "message_count", "proportion_of_messages"],
        ["From", "4", "1.0"],
        ["Subject", "1", "0.25"],
    ]


def test_creates_the_parent_directory(tmp_path):
    output_file = tmp_path / "01_extract_and_parse_usenet_data" / "counts.csv"

    write_header_field_counts(
        HeaderFieldCounts(message_count=1, field_counts={"From": 1}), output_file
    )

    assert output_file.exists()
