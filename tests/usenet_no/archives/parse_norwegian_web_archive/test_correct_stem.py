from usenet_no.archives.parse_norwegian_web_archive import correct_stem


def test_corrects_a_cut_off_stem():
    assert correct_stem("no.elektron", {"no.elektron": "no.elektronikk"}) == (
        "no.elektronikk"
    )


def test_leaves_other_stems_unchanged():
    assert correct_stem("no.alkohol", {"no.elektron": "no.elektronikk"}) == "no.alkohol"


def test_no_corrections_leaves_stem_unchanged():
    assert correct_stem("no.elektron", {}) == "no.elektron"
