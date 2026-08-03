from usenet_no.topic_modelling import make_run_tag


def test_the_method_leads_the_tag():
    assert make_run_tag("senstopic", None, ["no.bil"]) == "senstopic_no.bil"


def test_the_selection_is_sorted_so_the_order_it_is_passed_in_does_not_matter():
    assert make_run_tag("s3", None, ["no.musikk", "no.bil"]) == make_run_tag(
        "s3", None, ["no.bil", "no.musikk"]
    )


def test_a_number_of_topics_is_appended_and_leaving_it_out_shortens_the_tag():
    assert make_run_tag("gmm", 10, ["no.bil"]) == "gmm_no.bil_nr10"
    assert make_run_tag("gmm", None, ["no.bil"]) == "gmm_no.bil"


def test_runs_of_different_methods_do_not_share_a_tag():
    assert make_run_tag("gmm", 10, ["no.bil"]) != make_run_tag("s3", 10, ["no.bil"])
