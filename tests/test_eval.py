"""Placeholder tests for evaluation module."""

from evaluation.compute_metrics import compute_metrics
from evaluation.eval_runner import run_evaluation


def test_evaluation_functions_exist() -> None:
    """Check that evaluation functions are callable."""
    assert callable(compute_metrics)
    assert callable(run_evaluation)


def test_compute_metrics_non_zero_scores() -> None:
    """Compute metrics on simple texts and expect non-zero scores."""
    references = ["hello there how are you", "the weather is nice today"]
    predictions = ["hello there how are you", "the weather is nice today"]

    scores = compute_metrics(references, predictions)

    assert scores["bleu"] > 0
    assert scores["rougeL"] > 0
    assert scores["bert_score_f1"] > 0
