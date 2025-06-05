"""Tests for evaluation runner and metrics computation."""

from unittest.mock import MagicMock, patch
import pytest

pytest.importorskip("bert_score")
pytest.importorskip("rouge_score")
pytest.importorskip("sacrebleu")

from evaluation.eval_runner import run_evaluation
from evaluation.compute_metrics import compute_metrics


def test_run_evaluation_computes_metrics() -> None:
    """Run evaluation with mocked models and verify metric calculation."""
    prompts = [{"prompt": "Hi", "reference": "Hello"}]

    with patch("evaluation.eval_runner.load_prompts", return_value=prompts), \
         patch("evaluation.eval_runner.AutoModelForCausalLM", MagicMock()), \
         patch("evaluation.eval_runner.AutoTokenizer", MagicMock()), \
         patch("evaluation.eval_runner.generate_responses", side_effect=[["base"], ["merged"]]), \
         patch("evaluation.eval_runner.compute_metrics", return_value={"score": 1.0}) as metric_mock:
        metrics = run_evaluation("base", "merged", "dummy.jsonl")

    assert metrics == {"score": 1.0}
    metric_mock.assert_called_once_with(["Hello"], ["merged"])


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


def test_compute_metrics_simple() -> None:
    """Metrics should return scores for identical sentences."""
    references = ["안녕하세요"]
    predictions = ["안녕하세요"]

    metrics = compute_metrics(references, predictions)

    assert isinstance(metrics, dict)
    assert metrics
    assert all(isinstance(v, float) for v in metrics.values())


def test_run_evaluation_smoke(monkeypatch) -> None:
    """``run_evaluation`` should invoke ``compute_metrics`` on prompts."""

    called = {"count": 0}

    def fake_compute_metrics(refs, preds):
        called["count"] += 1
        return {"bleu": 1.0}

    monkeypatch.setattr("evaluation.eval_runner.compute_metrics", fake_compute_metrics)

    run_evaluation("base", "merged", "dummy.jsonl")

    assert called["count"] == 1

