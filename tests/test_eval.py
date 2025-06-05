"""Placeholder tests for evaluation module."""

from evaluation.compute_metrics import compute_metrics
from evaluation.eval_runner import run_evaluation


def test_evaluation_functions_exist() -> None:
    """Check that evaluation functions are callable."""
    assert callable(compute_metrics)
    assert callable(run_evaluation)
