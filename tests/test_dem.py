"""Tests for the DEM (Data Efficiency Method) module."""

import pytest

pytest.importorskip("torch")

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


def test_training_diff_and_merge() -> None:
    """Run a tiny end-to-end cycle on toy tensors."""

    x = torch.eye(2)
    y = 2 * torch.eye(2)

    lora = train_individual_domain(x, y, epochs=5, lr=0.2, use_fsdp=False, mlflow_run="test")
    assert "lora_weight" in lora

    base = {"lora_weight": torch.zeros_like(lora["lora_weight"])}

    diff = compute_vector_diff(base, lora)
    for param in diff.values():
        assert not torch.all(param == 0)

    merged = merge_models(base, [(diff, 1.0)])
    assert torch.allclose(merged["lora_weight"], lora["lora_weight"], atol=1e-2)

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

