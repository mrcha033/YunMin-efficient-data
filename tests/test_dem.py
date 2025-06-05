"""Unit tests for simplified DEM workflow."""

import torch

from dem.train_individual import train_individual_domain
from dem.vector_diff import compute_vector_diff
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

    lora = train_individual_domain(x, y, epochs=300, lr=0.2)
    assert "lora_weight" in lora

    base = {"lora_weight": torch.zeros_like(lora["lora_weight"])}

    diff = compute_vector_diff(base, lora)
    for param in diff.values():
        assert not torch.all(param == 0)

    merged = merge_models(base, [(diff, 1.0)])
    assert torch.allclose(merged["lora_weight"], lora["lora_weight"], atol=1e-2)
