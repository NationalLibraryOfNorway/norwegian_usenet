from usenet_no.hash import make_hash


def test_creates_same_hash_for_same_string():
    test_str = "herhehr"
    first_hash = make_hash(test_str)
    second_hash = make_hash(test_str)
    assert first_hash == second_hash
