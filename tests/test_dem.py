"""Tests for the DEM (Data Efficiency Method) module."""

import pytest

pytest.importorskip("torch")

import yaml
from pathlib import Path

from dem.train_individual import train_individual_domain
from dem.vector_diff import compute_vector_diff
from dem.merge_model import merge_models


def test_dem_functions_exist() -> None:
    """Check that DEM functions are callable."""
    assert callable(train_individual_domain)
    assert callable(compute_vector_diff)
    assert callable(merge_models)


def test_training_creates_artifacts(tmp_path) -> None:
    """Run a tiny LoRA training and ensure files are written."""

    data_file = tmp_path / "data.jsonl"
    data_file.write_text('{"text": "hello"}\n{"text": "world"}\n', encoding="utf-8")
    config = {
        "base_model": {"name": "hf-internal-testing/tiny-random-gpt2"},
        "training": {"learning_rate": 1e-4, "batch_size": 1, "max_epochs": 1},
        "lora": {"r": 2, "alpha": 4, "dropout": 0.0, "target_modules": ["c_attn"]},
    }
    config_path = tmp_path / "cfg.yaml"
    with open(config_path, "w", encoding="utf-8") as f:
        yaml.safe_dump(config, f)

    model_dir = tmp_path / "model"
    log_dir = tmp_path / "logs"
    summary_dir = tmp_path / "summary"

    adapter = train_individual_domain(
        str(data_file),
        "demo",
        config_path=str(config_path),
        output_dir=str(model_dir),
        log_dir=str(log_dir),
        summary_dir=str(summary_dir),
    )

    assert Path(adapter).exists()
    assert (log_dir / "train_demo.log").exists()
    assert (summary_dir / "train_demo.csv").exists()

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

    merged = merge_models(base, [(diff1, 1.0), (diff2, 1.0)])

    expected = {"w1": 1.1, "w2": 1.8}
    assert merged == expected
