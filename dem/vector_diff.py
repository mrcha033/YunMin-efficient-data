"""Utilities for computing parameter difference vectors."""

from __future__ import annotations

from typing import Dict

import argparse
import json
from pathlib import Path

import torch
import numpy as np


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


def compute_stats(diff: Dict[str, torch.Tensor]) -> Dict[str, float]:
    """Return norm, max and min values of all tensors in ``diff``."""

    if not diff:
        return {"norm": 0.0, "max": 0.0, "min": 0.0}

    arr = np.concatenate([t.detach().cpu().numpy().ravel() for t in diff.values()])
    return {
        "norm": float(np.linalg.norm(arr)),
        "max": float(np.max(arr)),
        "min": float(np.min(arr)),
    }


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Compute parameter diff vector between base and LoRA models."
    )
    parser.add_argument("--base", required=True, help="Path to base model file")
    parser.add_argument("--lora", required=True, help="Path to LoRA model file")
    parser.add_argument("--domain", required=True, help="Domain identifier")
    parser.add_argument(
        "--diff-dir", default="diff_vectors", help="Directory to save diff .npy"
    )
    parser.add_argument(
        "--stats-dir", default="diff_stats", help="Directory to save stats JSON"
    )
    args = parser.parse_args()

    base = torch.load(args.base, map_location="cpu")
    lora = torch.load(args.lora, map_location="cpu")

    diff = compute_vector_diff(base, lora)

    diff_dir = Path(args.diff_dir)
    diff_dir.mkdir(parents=True, exist_ok=True)
    diff_path = diff_dir / f"diff_{args.domain}.npy"
    np.save(diff_path, {k: v.detach().cpu().numpy() for k, v in diff.items()})

    stats = compute_stats(diff)
    stats_dir = Path(args.stats_dir)
    stats_dir.mkdir(parents=True, exist_ok=True)
    stats_path = stats_dir / f"{args.domain}_summary.json"
    with stats_path.open("w", encoding="utf-8") as f:
        json.dump(stats, f, ensure_ascii=False, indent=2)

    print(f"Diff vector saved to {diff_path}")
    print(f"Stats saved to {stats_path}")


if __name__ == "__main__":  # pragma: no cover - CLI entry point
    main()
