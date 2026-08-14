from usenet_no.newsgroup_tree import load_counts, tree_lines


def test_the_total_row_is_not_a_newsgroup(tmp_path):
    count_file = tmp_path / "messages_per_group_nb.csv"
    count_file.write_text("newsgroup,message_count\nno.first.mbox,100\nTotal,100\n")

    assert load_counts(count_file) == {"no.first": 100}


def test_the_tree_is_drawn_with_counts_per_node():
    lines = tree_lines("NB", {"no.marked": 100, "no.marked.diverse": 7, "no.x": 3})

    assert lines == [
        "NB  (110 messages, 3 newsgroups)",
        "└── no  (110)",
        "    ├── .  (0)",
        "    ├── marked  (107)",
        "    │   ├── .  (100)",
        "    │   └── diverse  (7)",
        "    └── x  (3)",
    ]
