"""
MinHash utility functions for deduplication
"""

import re
from typing import List, Set
from datasketch import MinHash


def tokenize_ngrams(text: str, n: int = 5) -> List[str]:
    """
    Create n-grams from text for MinHash
    
    Args:
        text: Input text
        n: N-gram size
        
    Returns:
        List of n-gram strings
    """
    # Simple whitespace tokenization (can be enhanced with proper Korean tokenizer)
    tokens = text.lower().split()
    
    if len(tokens) < n:
        return [' '.join(tokens)]
    
    ngrams = []
    for i in range(len(tokens) - n + 1):
        ngram = ' '.join(tokens[i:i + n])
        ngrams.append(ngram)
    
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
    return minhash1.jaccard(minhash2) 