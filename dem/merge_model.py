"""Merge multiple difference vectors into a single model."""

from __future__ import annotations

from typing import Dict, Iterable, Tuple

import torch


def merge_models(
    base_model: Dict[str, torch.Tensor],
    diffs: Iterable[Tuple[Dict[str, torch.Tensor], float]],
) -> Dict[str, torch.Tensor]:
    """Apply weighted diff vectors to ``base_model`` and return merged params."""

    merged = {name: param.clone() for name, param in base_model.items()}

    for diff, weight in diffs:
        for name, delta in diff.items():
            merged[name] += weight * delta

    return merged


if __name__ == "__main__":  # pragma: no cover - manual usage
    merge_models({}, [])


