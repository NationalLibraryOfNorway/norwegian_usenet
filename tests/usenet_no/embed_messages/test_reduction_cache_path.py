from pathlib import Path

import pytest

from usenet_no.embed_messages import (
    REDUCTION_AXIS_TITLES,
    REDUCTION_CHOICES,
    reduction_cache_path,
)

BASE = Path("data/output/08_make_embeddings")
MODEL = "some-org/some-model"


def test_umap_keeps_the_path_the_earlier_runs_wrote():
    assert reduction_cache_path(BASE, MODEL, ["no.bil"], "nb", "umap") == (
        BASE / "umap_embeddings" / MODEL / "no.bil_nb.npy"
    )


def test_each_reduction_caches_in_its_own_directory():
    paths = {
        reduction_cache_path(BASE, MODEL, ["no.bil"], "nb", reduction)
        for reduction in REDUCTION_CHOICES
    }
    assert len(paths) == len(REDUCTION_CHOICES)


def test_selection_order_does_not_change_the_path():
    selection = ["no.musikk", "no.bil", "no.slekt"]
    assert reduction_cache_path(BASE, MODEL, selection, "nb", "tsne") == (
        reduction_cache_path(BASE, MODEL, sorted(selection), "nb", "tsne")
    )


def test_each_archive_caches_in_its_own_file():
    paths = {
        reduction_cache_path(BASE, MODEL, ["no.bil"], archive, "tsne")
        for archive in ("nb", "ia", "both")
    }
    assert len(paths) == 3


def test_unknown_reduction_raises():
    with pytest.raises(ValueError, match="pca"):
        reduction_cache_path(BASE, MODEL, ["no.bil"], "nb", "pca")


def test_every_reduction_has_an_axis_title():
    assert set(REDUCTION_AXIS_TITLES) == set(REDUCTION_CHOICES)
