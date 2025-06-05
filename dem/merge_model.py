"""Merge multiple difference vectors into a single model."""

from __future__ import annotations

from typing import Dict, Iterable, Tuple, List
from decimal import Decimal
import argparse
from pathlib import Path

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


def load_state_dict(path: str) -> Dict[str, torch.Tensor]:
    """Load a PyTorch state dict from ``path`` on CPU."""
    return torch.load(path, map_location="cpu")


def save_state_dict(path: str, state_dict: Dict[str, torch.Tensor]) -> None:
    """Save ``state_dict`` to ``path`` creating parent directories."""
    out = Path(path)
    out.parent.mkdir(parents=True, exist_ok=True)
    torch.save(state_dict, out)


def parse_diff_arg(arg: str) -> tuple[str, float]:
    """Return diff vector path and weight from ``PATH:WEIGHT`` string."""
    try:
        path, weight = arg.split(":")
        return path, float(weight)
    except ValueError as exc:  # pragma: no cover - simple parsing
        raise argparse.ArgumentTypeError(
            "Diff argument must be in PATH:WEIGHT format"
        ) from exc


def main() -> None:  # pragma: no cover - CLI
    parser = argparse.ArgumentParser(description="Merge diff vectors and run evaluation")
    parser.add_argument("--base-model", default="models/base/pytorch_model.bin", help="Path to base model weights")
    parser.add_argument("--output-dir", default="models/merged", help="Directory to save merged model")
    parser.add_argument(
        "--diff",
        action="append",
        required=True,
        help="Diff vector and weight in PATH:WEIGHT format; can be repeated",
    )
    parser.add_argument(
        "--prompt-file",
        default="evaluation/eval_prompts.jsonl",
        help="Prompts for comparison after merging",
    )
    parser.add_argument(
        "--markdown-out",
        default="eval/eval_prompt_comparison.md",
        help="Markdown file to write prompt comparison",
    )
    args = parser.parse_args()

    base = load_state_dict(args.base_model)

    diffs: List[Tuple[Dict[str, torch.Tensor], float]] = []
    for d in args.diff:
        path, weight = parse_diff_arg(d)
        diffs.append((load_state_dict(path), weight))

    merged = merge_models(base, diffs)

    out_path = Path(args.output_dir) / "pytorch_model.bin"
    save_state_dict(str(out_path), merged)

    # Run evaluation to create markdown comparison
    from evaluation.eval_runner import save_prompt_comparison

    save_prompt_comparison(
        args.base_model,
        args.output_dir,
        args.prompt_file,
        args.markdown_out,
    )


if __name__ == "__main__":  # pragma: no cover - manual usage
    main()


