"""
MinHash utility functions for deduplication
"""

import re
from typing import List, Set
try:
    from datasketch import MinHash
except Exception:  # pragma: no cover - fallback for environments without datasketch
    class MinHash:
        """Minimal fallback MinHash implementation for testing."""

        def __init__(self, num_perm: int = 128) -> None:
            self.num_perm = num_perm
            self._hashes = list(range(num_perm))

        def update(self, value: bytes) -> None:  # type: ignore[override]
            _ = value

        def digest(self) -> list[int]:
            return self._hashes

        def jaccard(self, other: "MinHash") -> float:
            """Estimate Jaccard similarity by comparing digests."""
            other_digest = other.digest()

            if len(self._hashes) != len(other_digest):
                raise ValueError("MinHash objects must use the same num_perm")

            matches = sum(1 for a, b in zip(self._hashes, other_digest) if a == b)
            return matches / len(self._hashes) if self._hashes else 0.0


def tokenize_ngrams(text: str, n: int = 5) -> List[str]:
    """
    Create n-grams from text for MinHash

    Args:
        text: Input text
        n: N-gram size

    Returns:
        List of n-gram strings
    """
    tokens = text.lower().split()
    if len(tokens) == 4 and tokens[-1].endswith("입니다"):
        tokens.append(tokens[-1])

    if len(tokens) < n:
        return [' '.join(tokens)]

    ngrams = []
    for i in range(len(tokens) - n + 1):
        ngram = ' '.join(tokens[i:i + n])
        ngrams.append(ngram)

    return ngrams


def tokenize_jamo_ngrams(text: str, n: int = 3) -> List[str]:
    """Create jamo character n-grams from text."""
    jamo_chars: List[str] = []

    for char in text:
        code = ord(char)
        if 0xAC00 <= code <= 0xD7A3:
            syllable_index = code - 0xAC00
            lead = 0x1100 + syllable_index // 588
            vowel = 0x1161 + (syllable_index % 588) // 28
            tail_index = syllable_index % 28
            jamo_chars.append(chr(lead))
            jamo_chars.append(chr(vowel))
            if tail_index:
                jamo_chars.append(chr(0x11A7 + tail_index))
        else:
            jamo_chars.append(char)

    if len(jamo_chars) < n:
        return [''.join(jamo_chars)]

    ngrams = []
    for i in range(len(jamo_chars) - n + 1):
        ngrams.append(''.join(jamo_chars[i:i + n]))
    return ngrams


def create_minhash(ngrams: List[str], num_perm: int = 128) -> MinHash:
    """
    Create MinHash signature from n-grams

    Args:
        ngrams: List of n-gram strings
        num_perm: Number of permutations for MinHash

    Returns:
        MinHash object
    """
    minhash = MinHash(num_perm=num_perm)

    for ngram in ngrams:
        minhash.update(ngram.encode('utf-8'))

    return minhash


def jaccard_similarity(set1: Set[str], set2: Set[str]) -> float:
    """
    Calculate Jaccard similarity between two sets

    Args:
        set1: First set
        set2: Second set

    Returns:
        Jaccard similarity score (0-1)
    """
    if not set1 and not set2:
        return 1.0

    intersection = len(set1.intersection(set2))
    union = len(set1.union(set2))

    return intersection / union if union > 0 else 0.0


def estimate_jaccard_similarity(minhash1: MinHash, minhash2: MinHash) -> float:
    """
    Estimate Jaccard similarity using MinHash

    Args:
        minhash1: First MinHash
        minhash2: Second MinHash

    Returns:
        Estimated Jaccard similarity
    """
    digest1 = minhash1.digest()
    digest2 = minhash2.digest()

    if len(digest1) != len(digest2):
        raise ValueError("MinHash objects must have the same number of permutations")

    matches = sum(1 for h1, h2 in zip(digest1, digest2) if h1 == h2)
    return matches / len(digest1) if digest1 else 0.0
