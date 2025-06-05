"""Compute evaluation metrics for model outputs."""

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


if __name__ == "__main__":
    # Example placeholder for manual testing
    refs = ["안녕하세요"]
    preds = ["안녕하세요"]
    print(compute_metrics(refs, preds))
