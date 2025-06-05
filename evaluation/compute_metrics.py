"""Compute evaluation metrics for model outputs."""

from typing import List, Dict


def compute_metrics(references: List[str], predictions: List[str]) -> Dict[str, float]:
    """Compute text generation metrics.

    Args:
        references: Ground truth texts.
        predictions: Generated texts by a model.

    Returns:
        Dictionary of metric names to scores.
    """
    # TODO: implement metric calculations using sacrebleu or other libraries
    return {}


if __name__ == "__main__":
    # Example placeholder for manual testing
    refs = ["안녕하세요"]
    preds = ["안녕하세요"]
    print(compute_metrics(refs, preds))
