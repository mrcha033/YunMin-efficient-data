"""Compute evaluation metrics for model outputs."""

from typing import Dict, List


def compute_metrics(references: List[str], predictions: List[str]) -> Dict[str, float]:
    """Compute BLEU and ROUGE-L metrics for generated texts.

    Args:
        references: Ground truth texts.
        predictions: Generated texts by a model.

    Returns:
        Dictionary mapping metric names to scores.
    """
    try:
        import sacrebleu
        from rouge_score import rouge_scorer
    except ImportError as exc:  # pragma: no cover - optional dependency
        raise ImportError(
            "sacrebleu and rouge-score are required for metric computation"
        ) from exc

    bleu = sacrebleu.corpus_bleu(predictions, [references]).score

    scorer = rouge_scorer.RougeScorer(["rougeL"], use_stemmer=True)
    rouge_scores = [
        scorer.score(ref, pred)["rougeL"].fmeasure
        for ref, pred in zip(references, predictions)
    ]
    rouge_l = sum(rouge_scores) / len(rouge_scores) if rouge_scores else 0.0

    return {
        "bleu": bleu,
        "rougeL": rouge_l,
    }


if __name__ == "__main__":
    # Example placeholder for manual testing
    refs = ["안녕하세요"]
    preds = ["안녕하세요"]
    print(compute_metrics(refs, preds))
