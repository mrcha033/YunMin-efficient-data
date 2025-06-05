"""Simplified LoRA fine-tuning utilities."""

from __future__ import annotations

from typing import Dict

import torch


def train_individual_domain(
    inputs: torch.Tensor,
    targets: torch.Tensor,
    epochs: int = 200,
    lr: float = 0.1,
) -> Dict[str, torch.Tensor]:
    """Train a dummy LoRA adapter using linear regression.

    This simplified function performs gradient descent to learn a single
    projection matrix that maps ``inputs`` to ``targets``.  It is intended for
    unit tests and example usage only.

    Args:
        inputs: Input feature tensor of shape ``(n_samples, in_dim)``.
        targets: Target tensor of shape ``(n_samples, out_dim)``.
        epochs: Number of gradient descent steps to run.
        lr: Learning rate.

    Returns:
        Dictionary containing the learned ``"lora_weight"`` parameter.
    """

    weight = torch.zeros(inputs.size(1), targets.size(1), requires_grad=True)

    for _ in range(epochs):
        preds = inputs @ weight
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


