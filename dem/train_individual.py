"""Simplified LoRA fine-tuning utilities."""

from __future__ import annotations

from typing import Dict, Union, Optional
from pathlib import Path
import json

import torch
from torch.distributed.fsdp import FullyShardedDataParallel as FSDP
import mlflow


def train_individual_domain(
    inputs: Union[torch.Tensor, str],
    targets_or_outdir: Union[torch.Tensor, str],
    epochs: int = 200,
    lr: float = 0.1,
    use_fsdp: bool = False,
    mlflow_run: Optional[str] = None,
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
        use_fsdp: Wrap model with FSDP/ZeRO-3 if True.
        mlflow_run: Optional MLflow run name for metric logging.

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

    linear = torch.nn.Linear(inputs_t.size(1), targets.size(1), bias=False)
    if use_fsdp:
        if not torch.distributed.is_initialized():
            torch.distributed.init_process_group("gloo", rank=0, world_size=1)
        linear = FSDP(linear)
    optimizer = torch.optim.SGD(linear.parameters(), lr=lr)

    run = mlflow.start_run(run_name=mlflow_run) if mlflow_run else None
    for step in range(epochs):
        optimizer.zero_grad()
        preds = linear(inputs_t)
        loss = torch.mean((preds - targets) ** 2)
        loss.backward()
        optimizer.step()
        if run:
            mlflow.log_metric("loss", loss.item(), step=step)

    if run:
        mlflow.end_run()

    weight = linear.weight.detach().cpu()
    return {"lora_weight": weight}


if __name__ == "__main__":  # pragma: no cover - manual usage
    x = torch.eye(2)
    y = 2 * torch.eye(2)
    result = train_individual_domain(x, y)
    print(result)
