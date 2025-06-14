"""Utilities to compute text generation evaluation metrics."""

from __future__ import annotations

import argparse
import csv
from pathlib import Path
from typing import Dict, List

from bert_score import score as bert_score
from rouge_score import rouge_scorer
from sacrebleu import corpus_bleu


def compute_metrics(references: List[str], predictions: List[str]) -> Dict[str, float]:
    """Compute BLEU, ROUGE, and BERTScore metrics.

    Args:
        references: Ground truth texts.
        predictions: Generated texts by a model.

    Returns:
        Dictionary mapping metric names to scores.
    """
    if len(references) != len(predictions):
        raise ValueError("Reference and prediction counts do not match")

    bleu = corpus_bleu(predictions, [references], smooth_method="exp").score

    scorer = rouge_scorer.RougeScorer(["rouge1", "rouge2", "rougeL"], use_stemmer=True)
    rouge1 = rouge2 = rougel = 0.0
    for ref, pred in zip(references, predictions):
        scores = scorer.score(ref, pred)
        rouge1 += scores["rouge1"].fmeasure
        rouge2 += scores["rouge2"].fmeasure
        rougel += scores["rougeL"].fmeasure
    n = max(len(references), 1)
    rouge1 /= n
    rouge2 /= n
    rougel /= n

    _, _, bert_f1 = bert_score(predictions, references, lang="ko", verbose=False)
    bert_f1 = float(bert_f1.mean())

    return {
        "bleu": float(bleu),
        "rouge1": rouge1,
        "rouge2": rouge2,
        "rougeL": rougel,
        "bert_score_f1": bert_f1,
    }


def _load_lines(path: str) -> List[str]:
    """Load lines from a UTF-8 text file."""
    with open(path, "r", encoding="utf-8") as f:
        return [line.strip() for line in f if line.strip()]


def main(args: argparse.Namespace | None = None) -> None:
    """Entry point for CLI usage."""
    parser = argparse.ArgumentParser(
        description="Compute BLEU, ROUGE and BERTScore given prediction and reference files.",
    )
    parser.add_argument(
        "--predictions",
        required=True,
        help="Path to a file containing one prediction per line.",
    )
    parser.add_argument(
        "--references",
        required=True,
        help="Path to a file containing one reference per line.",
    )
    parser.add_argument(
        "--output",
        required=True,
        help="Destination CSV file for metric results.",
    )
    parsed = parser.parse_args([] if args is None else args)

    predictions = _load_lines(parsed.predictions)
    references = _load_lines(parsed.references)
    metrics = compute_metrics(references, predictions)

    output_path = Path(parsed.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", encoding="utf-8", newline="") as csvfile:
        writer = csv.DictWriter(csvfile, fieldnames=list(metrics.keys()))
        writer.writeheader()
        writer.writerow(metrics)


if __name__ == "__main__":
    main()
