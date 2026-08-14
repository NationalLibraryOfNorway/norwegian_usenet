from usenet_no.newsgroup_tree import OWN_MBOX_LABEL, build_tree


def test_a_newsgroup_hangs_under_its_supergroups():
    tree = build_tree({"no.marked.diverse": 7})

    diverse = tree.children["no"].children["marked"].children["diverse"]
    assert diverse.own_count == 7
    assert tree.total() == 7


def test_a_supergroup_holds_its_own_mbox_count_in_a_dot_child():
    tree = build_tree({"no.marked": 100, "no.marked.diverse": 7})

    marked = tree.children["no"].children["marked"]
    assert marked.children[OWN_MBOX_LABEL].total() == 100
    assert marked.own_count == 0
    assert marked.total() == 107


def test_the_dot_child_comes_first():
    tree = build_tree({"no.marked": 100, "no.marked.aaa": 7})

    marked = tree.children["no"].children["marked"]
    assert list(marked.children) == [OWN_MBOX_LABEL, "aaa"]


def test_a_supergroup_without_an_mbox_of_its_own_gets_a_zero_dot_child():
    tree = build_tree({"no.marked.diverse": 7})

    marked = tree.children["no"].children["marked"]
    assert marked.children[OWN_MBOX_LABEL].total() == 0


def test_a_newsgroup_without_subgroups_gets_no_dot_child():
    tree = build_tree({"no.marked": 100})

    assert tree.children["no"].children["marked"].children == {}


def test_the_root_gets_no_dot_child():
    tree = build_tree({"no.marked": 100})

    assert list(tree.children) == ["no"]
