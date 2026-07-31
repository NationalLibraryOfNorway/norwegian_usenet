import json

import pytest

from usenet_no.replacement_chars.robustness import read_model_runs, read_summary

CSV_TEXT = """\
newsgroup,message_id_hash,replacement_char_count,nb_body_length,matched_similarity,shuffled_similarity
no.alkohol,hash-a,12,1843,0.5473,0.2201
no.bil,hash-b,1,97,0.9912,0.3010
"""


def make_summary(model: str, matched_mean: float, shuffled_mean: float) -> dict:
    statistics = {
        "std": 0.01,
        "min": 0.1,
        "max": 0.99,
        "percentiles": {"p05": 0.5, "p95": 0.9},
    }
    return {
        "model": model,
        "num_pairs": 2,
        "matched": {"mean": matched_mean} | statistics,
        "shuffled": {"mean": shuffled_mean} | statistics,
    }


def write_run(
    directory, model: str, matched_mean=0.99, shuffled_mean=0.5, similarities=CSV_TEXT
) -> None:
    model_directory = directory / model
    model_directory.mkdir(parents=True)
    (model_directory / "summary.json").write_text(
        json.dumps(make_summary(model, matched_mean, shuffled_mean)), encoding="utf-8"
    )
    if similarities is not None:
        (model_directory / "similarities.csv").write_text(
            similarities, encoding="utf-8"
        )


@pytest.fixture
def results_directory(tmp_path):
    write_run(tmp_path, "org-a/model-one", matched_mean=0.99, shuffled_mean=0.5)
    write_run(tmp_path, "org-b/model-two", matched_mean=0.95, shuffled_mean=0.4)
    return tmp_path


def test_reads_every_model_directory(results_directory):
    runs = read_model_runs(results_directory)

    assert [run.summary.model for run in runs] == ["org-a/model-one", "org-b/model-two"]


def test_reads_both_files_of_a_run(results_directory):
    first, _ = read_model_runs(results_directory)

    assert first.summary.matched.mean == pytest.approx(0.99)
    assert first.summary.shuffled.mean == pytest.approx(0.5)
    assert [row.message_id_hash for row in first.similarities] == ["hash-a", "hash-b"]


def test_runs_come_back_in_model_name_order(tmp_path):
    write_run(tmp_path, "zeta/model")
    write_run(tmp_path, "alpha/model")

    runs = read_model_runs(tmp_path)

    assert [run.summary.model for run in runs] == ["alpha/model", "zeta/model"]


def test_a_run_without_similarities_is_left_out(tmp_path):
    write_run(tmp_path, "org/scored")
    write_run(tmp_path, "org/unscored", similarities=None)

    runs = read_model_runs(tmp_path)

    assert [run.summary.model for run in runs] == ["org/scored"]


def test_a_directory_without_runs_reads_as_nothing(tmp_path):
    assert read_model_runs(tmp_path) == []


def test_read_summary_reads_the_nested_statistics(results_directory):
    summary = read_summary(results_directory / "org-a/model-one/summary.json")

    assert summary.model == "org-a/model-one"
    assert summary.num_pairs == 2
    assert summary.matched.percentiles["p95"] == pytest.approx(0.9)
    assert summary.shuffled.min == pytest.approx(0.1)
