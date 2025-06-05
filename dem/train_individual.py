"""Simplified LoRA fine-tuning utilities."""

from __future__ import annotations

from typing import Dict, Union
from pathlib import Path
import json

import torch


def train_individual_domain(
    inputs: Union[torch.Tensor, str],
    targets_or_outdir: Union[torch.Tensor, str],
    epochs: int = 200,
    lr: float = 0.1,
) -> Dict[str, torch.Tensor]:
    """Train a dummy LoRA adapter.

    The function supports two modes for unit tests:

    1. **Tensor mode** – ``inputs`` and ``targets_or_outdir`` are tensors. A
       tiny linear regression loop is run and the resulting weight is
       returned.
    2. **File mode** – ``inputs`` is treated as a path to a JSONL file and
       ``targets_or_outdir`` as an output directory path.  The function creates
       the directory and saves a dummy weight derived from the text length.  In
       this mode ``epochs`` and ``lr`` are ignored.

    Args:
        inputs: Either input tensor or JSONL path.
        targets_or_outdir: Either target tensor or output directory path.
        epochs: Number of gradient descent steps to run (tensor mode only).
        lr: Learning rate (tensor mode only).

    Returns:
        Dictionary containing a ``"lora_weight"`` tensor.
    """

    if isinstance(inputs, str):
        data_path = Path(inputs)
        out_dir = Path(str(targets_or_outdir))
        out_dir.mkdir(parents=True, exist_ok=True)

        texts = []
        with data_path.open("r", encoding="utf-8") as f:
            for line in f:
                try:
                    obj = json.loads(line)
                    texts.append(obj.get("text", ""))
                except json.JSONDecodeError:
                    continue

        length = float(len(" ".join(texts)))
        weight = torch.tensor([[length]])
        torch.save({"lora_weight": weight}, out_dir / "adapter.pt")
        return {"lora_weight": weight}

    # tensor mode
    inputs_t = inputs
    targets = targets_or_outdir  # type: ignore[assignment]

    weight = torch.zeros(inputs_t.size(1), targets.size(1), requires_grad=True)

    for _ in range(epochs):
        preds = inputs_t @ weight
        loss = torch.mean((preds - targets) ** 2)
        loss.backward()

        with torch.no_grad():
            weight -= lr * weight.grad
            weight.grad.zero_()

    return {"lora_weight": weight.detach()}


if __name__ == "__main__":  # pragma: no cover - manual usage
    x = torch.eye(2)
    y = 2 * torch.eye(2)
    result = train_individual_domain(x, y)
    print(result)


