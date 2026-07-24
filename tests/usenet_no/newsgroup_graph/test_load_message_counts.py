from usenet_no.newsgroup_graph import load_message_counts


def test_the_mbox_suffix_is_dropped(tmp_path):
    count_file = tmp_path / "messages_per_group_nb.csv"
    count_file.write_text("newsgroup,message_count\nno.first.mbox,100\n")

    counts = load_message_counts([count_file])

    assert counts == {"no.first": 100}


def test_counts_are_summed_across_files(tmp_path):
    """no.first is counted in both archives, no.second in one."""
    nb_file = tmp_path / "messages_per_group_nb.csv"
    nb_file.write_text("newsgroup,message_count\nno.first.mbox,100\n")
    ia_file = tmp_path / "messages_per_group_ia.csv"
    ia_file.write_text("newsgroup,message_count\nno.first.mbox,40\nno.second.mbox,7\n")

    counts = load_message_counts([nb_file, ia_file])

    assert counts == {"no.first": 140, "no.second": 7}
