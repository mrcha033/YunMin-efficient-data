"""Utilities for computing parameter difference vectors."""

from __future__ import annotations

from typing import Dict

import torch


def compute_vector_diff(
    base_model: Dict[str, torch.Tensor],
    fine_tuned_model: Dict[str, torch.Tensor],
) -> Dict[str, torch.Tensor]:
    """Return ``fine_tuned_model`` parameters minus ``base_model`` parameters."""

    diff: Dict[str, torch.Tensor] = {}
    for name, base_param in base_model.items():
        tuned_param = fine_tuned_model[name]
        diff[name] = tuned_param - base_param
    return diff
