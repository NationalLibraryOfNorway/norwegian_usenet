from usenet_no.parse_norwegian_web_archive import load_newsgroup_corrections


def test_reads_the_csv_into_a_mapping(tmp_path):
    corrections_file = tmp_path / "cut_off_newsgroup_names.csv"
    corrections_file.write_text(
        "cut_off_name,full_name\n"
        "no.elektron,no.elektronikk\n"
        "no.alt.diskusjo,no.alt.diskusjoner\n"
    )

    assert load_newsgroup_corrections(corrections_file) == {
        "no.elektron": "no.elektronikk",
        "no.alt.diskusjo": "no.alt.diskusjoner",
    }


def test_missing_file_gives_no_corrections(tmp_path):
    assert load_newsgroup_corrections(tmp_path / "missing.csv") == {}
