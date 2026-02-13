from usenet_no.make_user_mapping import get_hash


def test_creates_same_hash_for_same_string():
    test_str = "herhehr"
    first_hash = get_hash(test_str)
    second_hash = get_hash(test_str)
    assert first_hash == second_hash
