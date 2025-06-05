"""
YunMin-EfficientData Deduplication Module

This module provides SlimPajama-based deduplication functionality using MinHash and LSH.
"""

from .minhash_utils import tokenize_ngrams, create_minhash, jaccard_similarity
from .cluster_reduction import select_representative_document

try:
    from .distributed_dedup import run_dedup_ray
except Exception:  # pragma: no cover - optional dependency
    run_dedup_ray = None

try:  # Optional heavy dependency
    from .slimpajama_dedup import main as run_deduplication
except Exception:  # pragma: no cover - dependency may be missing
    run_deduplication = None

__version__ = "1.0.0"
__all__ = [
    "run_deduplication",
    "run_dedup_ray",
    "tokenize_ngrams",
    "create_minhash",
    "jaccard_similarity",
    "select_representative_document"
]
