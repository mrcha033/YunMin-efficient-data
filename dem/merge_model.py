"""Merge multiple difference vectors into a single model."""

from __future__ import annotations

from typing import Dict, Iterable, Tuple
from decimal import Decimal

import torch


def merge_models(
    base_model: Dict[str, torch.Tensor],
    diffs: Iterable[Tuple[Dict[str, torch.Tensor], float]],
) -> Dict[str, torch.Tensor]:
    """Apply weighted diff vectors to ``base_model`` and return merged params."""

    merged = {
        name: param.clone() if hasattr(param, "clone") else Decimal(str(param))
        for name, param in base_model.items()
    }

    for diff, weight in diffs:
        for name, delta in diff.items():
            if isinstance(merged[name], Decimal):
                merged[name] += Decimal(str(weight * delta))
            else:
                merged[name] = merged[name] + weight * delta

    return {
        name: float(val) if isinstance(val, Decimal) else val for name, val in merged.items()
    }


if __name__ == "__main__":  # pragma: no cover - manual usage
    merge_models({}, [])


