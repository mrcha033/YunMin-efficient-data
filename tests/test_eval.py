"""Tests for evaluation runner and metrics computation."""

from unittest.mock import MagicMock, patch
import sys
sys.path.append('..')

from evaluation.eval_runner import run_evaluation


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
