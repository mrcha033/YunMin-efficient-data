"""Run evaluation between base and merged models."""

from typing import Iterable


def run_evaluation(prompts: Iterable[str]) -> None:
    """Generate model responses and compute metrics.

    Args:
        prompts: Iterable of prompt strings.
    """
    # TODO: implement evaluation logic integrating models and metrics
    for prompt in prompts:
        _ = prompt  # Placeholder
    

if __name__ == "__main__":
    run_evaluation(["안녕하세요?"])
