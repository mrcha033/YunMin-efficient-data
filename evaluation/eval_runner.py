"""Utilities to generate model responses and compute evaluation metrics."""

from __future__ import annotations

import argparse
import json
from typing import Any, Dict, Iterable, List

from evaluation.compute_metrics import compute_metrics

try:  # Optional dependency
    from transformers import AutoModelForCausalLM, AutoTokenizer
except Exception:  # pragma: no cover - allow import without transformers
    AutoModelForCausalLM = AutoTokenizer = None  # type: ignore

DEFAULT_PROMPT_FILE = "evaluation/eval_prompts.jsonl"


def load_prompts(prompt_file: str = DEFAULT_PROMPT_FILE) -> List[dict]:
    """Load prompts (and optional references) from a JSONL file."""
    prompts: List[dict] = []
    with open(prompt_file, "r", encoding="utf-8") as file:
        for line in file:
            prompts.append(json.loads(line))
    return prompts


def generate_responses(model: Any, tokenizer: Any, prompts: Iterable[str]) -> List[str]:
    """Generate responses for the given prompts using a model."""
    responses: List[str] = []
    for prompt in prompts:
        inputs = tokenizer(prompt, return_tensors="pt")
        output_ids = model.generate(**inputs, max_new_tokens=32)
        responses.append(tokenizer.decode(output_ids[0], skip_special_tokens=True))
    return responses


def run_evaluation(
    base_model_path: str,
    merged_model_path: str,
    prompt_file: str = DEFAULT_PROMPT_FILE,
) -> Dict[str, float]:
    """Run evaluation comparing base and merged models."""
    prompt_entries = load_prompts(prompt_file)
    prompts = [p["prompt"] for p in prompt_entries]
    references = [p.get("reference") for p in prompt_entries]

    if AutoModelForCausalLM is None or AutoTokenizer is None:
        raise ImportError(
            "transformers is required for running evaluation"
        )

    base_tokenizer = AutoTokenizer.from_pretrained(base_model_path)
    base_model = AutoModelForCausalLM.from_pretrained(base_model_path)
    merged_tokenizer = AutoTokenizer.from_pretrained(merged_model_path)
    merged_model = AutoModelForCausalLM.from_pretrained(merged_model_path)

    base_outputs = generate_responses(base_model, base_tokenizer, prompts)
    merged_outputs = generate_responses(merged_model, merged_tokenizer, prompts)

    refs = references if any(references) else base_outputs

    metrics = compute_metrics(refs, merged_outputs)
    print(metrics)
    return metrics


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Run evaluation of merged model against base model.")
    parser.add_argument("--base-model", required=True, help="Path to base model")
    parser.add_argument("--merged-model", required=True, help="Path to merged model")
    parser.add_argument("--prompts", default=DEFAULT_PROMPT_FILE, help="Path to evaluation prompts JSONL file")
    args = parser.parse_args()

    run_evaluation(args.base_model, args.merged_model, args.prompts)
