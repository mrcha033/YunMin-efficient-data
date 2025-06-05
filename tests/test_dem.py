"""Tests for the DEM (Data Efficiency Method) module."""

from dem.train_individual import train_individual_domain
from dem.vector_diff import compute_vector_diff
from dem.merge_model import merge_models


def test_dem_functions_exist() -> None:
    """Check that DEM functions are callable."""
    assert callable(train_individual_domain)
    assert callable(compute_vector_diff)
    assert callable(merge_models)


def test_compute_vector_diff_basic() -> None:
    """Verify simple difference calculation between two models."""
    base = {"w1": 1.0, "w2": 2.0}
    tuned = {"w1": 1.5, "w2": 3.0}

    diff = compute_vector_diff(base, tuned)

    assert diff == {"w1": 0.5, "w2": 1.0}


def test_merge_models_additive() -> None:
    """Ensure model merging adds diff vectors to the base model."""
    base = {"w1": 1.0, "w2": 2.0}
    diff1 = {"w1": 0.2, "w2": -0.5}
    diff2 = {"w1": -0.1, "w2": 0.3}

    merged = merge_models(base, [diff1, diff2])

    expected = {"w1": 1.1, "w2": 1.8}
    assert merged == expected


def test_train_individual_domain_creates_output(tmp_path) -> None:
    """Training function should create the given output directory."""
    data_file = tmp_path / "sample.jsonl"
    data_file.write_text('{"text": "hello"}\n', encoding="utf-8")
    out_dir = tmp_path / "model"

    result = train_individual_domain(str(data_file), str(out_dir))

    assert out_dir.exists()
    assert result is not None
