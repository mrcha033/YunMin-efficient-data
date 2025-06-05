"""Tests for the DEM (Data Efficiency Method) module."""

import pytest

pytest.importorskip("torch")

import yaml
from pathlib import Path
import torch
import subprocess
import sys
import json
import numpy as np

from dem.train_individual import train_individual_domain
from dem.vector_diff import compute_vector_diff, compute_stats
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

def test_train_individual_domain_creates_output(tmp_path) -> None:
    """Training function should create the given output directory."""
    data_file = tmp_path / "sample.jsonl"
    data_file.write_text('{"text": "hello"}\n', encoding="utf-8")
    out_dir = tmp_path / "model"

    result = train_individual_domain(str(data_file), str(out_dir), mlflow_run="file")

    assert out_dir.exists()
    assert result is not None


def test_vector_diff_cli_creates_files(tmp_path) -> None:
    """CLI should save diff numpy and stats JSON."""

    base = {"w": torch.zeros(1, 1)}
    lora = {"w": torch.ones(1, 1)}

    base_path = tmp_path / "base.pt"
    lora_path = tmp_path / "lora.pt"
    torch.save(base, base_path)
    torch.save(lora, lora_path)

    diff_dir = tmp_path / "diff"
    stats_dir = tmp_path / "stats"

    cmd = [
        sys.executable,
        "-m",
        "dem.vector_diff",
        "--base",
        str(base_path),
        "--lora",
        str(lora_path),
        "--domain",
        "demo",
        "--diff-dir",
        str(diff_dir),
        "--stats-dir",
        str(stats_dir),
    ]

    subprocess.run(cmd, check=True)

    diff_file = diff_dir / "diff_demo.npy"
    stats_file = stats_dir / "demo_summary.json"

    assert diff_file.exists()
    assert stats_file.exists()

    diff = np.load(diff_file, allow_pickle=True).item()
    assert diff["w"][0, 0] == 1.0

    with stats_file.open("r", encoding="utf-8") as f:
        stats = json.load(f)

    for key in ["norm", "max", "min"]:
        assert key in stats
