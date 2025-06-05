"""Tests for the evaluation utilities."""

from evaluation.compute_metrics import compute_metrics
from evaluation.eval_runner import run_evaluation


def test_evaluation_functions_exist() -> None:
    """Check that evaluation functions are callable."""
    assert callable(compute_metrics)
    assert callable(run_evaluation)


def test_compute_metrics_simple() -> None:
    """Metrics should return scores for identical sentences."""
    references = ["안녕하세요"]
    predictions = ["안녕하세요"]

    metrics = compute_metrics(references, predictions)

    assert isinstance(metrics, dict)
    assert metrics
    assert all(isinstance(v, float) for v in metrics.values())


def test_run_evaluation_smoke(monkeypatch) -> None:
    """run_evaluation should invoke compute_metrics on prompts."""

    called = {"count": 0}

    def fake_compute_metrics(refs, preds):
        called["count"] += 1
        return {"bleu": 1.0}

    monkeypatch.setattr("evaluation.eval_runner.compute_metrics", fake_compute_metrics)

    run_evaluation(["테스트"])

    assert called["count"] == 1
