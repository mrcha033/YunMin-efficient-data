"""Tests for evaluation runner and metrics computation."""

from unittest.mock import MagicMock, patch
from pathlib import Path
import subprocess
import pytest

pytest.importorskip("bert_score")
pytest.importorskip("rouge_score")
pytest.importorskip("sacrebleu")

from evaluation.eval_runner import run_evaluation, save_prompt_comparison
from evaluation.compute_metrics import compute_metrics


def test_run_evaluation_computes_metrics(tmp_path) -> None:
    """Run evaluation with mocked models and verify metric calculation."""
    prompts = [{"prompt": "Hi", "reference": "Hello"}]
    out_file = tmp_path / "metrics.json"

    with patch("evaluation.eval_runner.load_prompts", return_value=prompts), \
         patch("evaluation.eval_runner.AutoModelForCausalLM", MagicMock()), \
         patch("evaluation.eval_runner.AutoTokenizer", MagicMock()), \
         patch("evaluation.eval_runner.generate_responses", side_effect=[["base"], ["merged"]]), \
         patch("evaluation.eval_runner.compute_metrics", return_value={"score": 1.0}) as metric_mock:
        metrics = run_evaluation("base", "merged", "dummy.jsonl", str(out_file))

    assert metrics == {"score": 1.0}
    metric_mock.assert_called_once_with(["Hello"], ["merged"])
    assert out_file.exists()

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
    with patch("evaluation.eval_runner.load_prompts", return_value=[{"prompt": "t"}]), \
         patch("evaluation.eval_runner.AutoModelForCausalLM", MagicMock()), \
         patch("evaluation.eval_runner.AutoTokenizer", MagicMock()), \
         patch("evaluation.eval_runner.generate_responses", side_effect=[["base"], ["merged"]]):
        run_evaluation("base", "merged")

    run_evaluation("base", "merged", "dummy.jsonl")

    assert called["count"] == 1


def test_run_evaluation_no_reference_uses_base_outputs() -> None:
    """Without explicit references, base outputs become references."""

    prompts = [{"prompt": "Hi"}]

    with patch("evaluation.eval_runner.load_prompts", return_value=prompts), \
         patch("evaluation.eval_runner.AutoModelForCausalLM", MagicMock()), \
         patch("evaluation.eval_runner.AutoTokenizer", MagicMock()), \
         patch("evaluation.eval_runner.generate_responses", side_effect=[["base"], ["merged"]]), \
         patch("evaluation.eval_runner.compute_metrics", return_value={}) as metric_mock:
        run_evaluation("base", "merged")

    metric_mock.assert_called_once_with(["base"], ["merged"])


def test_save_prompt_comparison_writes_file(tmp_path) -> None:
    """``save_prompt_comparison`` should write markdown file."""

    out_file = tmp_path / "cmp.md"
    with patch("evaluation.eval_runner.load_prompts", return_value=[{"prompt": "p"}]), \
         patch("evaluation.eval_runner.AutoModelForCausalLM", MagicMock()), \
         patch("evaluation.eval_runner.AutoTokenizer", MagicMock()), \
         patch("evaluation.eval_runner.generate_responses", side_effect=[["b"], ["m"]]):
        save_prompt_comparison("base", "merged", "dummy.jsonl", str(out_file))

    assert out_file.exists()
def test_compute_metrics_cli(tmp_path) -> None:
    """CLI entrypoint should write a CSV of metrics."""
    pred_file = tmp_path / "pred.txt"
    ref_file = tmp_path / "ref.txt"
    out_csv = tmp_path / "metrics.csv"

    pred_file.write_text("hello\n", encoding="utf-8")
    ref_file.write_text("hello\n", encoding="utf-8")

    subprocess.run(
        [
            "python",
            "-m",
            "evaluation.compute_metrics",
            "--predictions",
            str(pred_file),
            "--references",
            str(ref_file),
            "--output",
            str(out_csv),
        ],
        check=True,
    )

    assert out_csv.exists()
    text = out_csv.read_text(encoding="utf-8")
    assert "bleu" in text
