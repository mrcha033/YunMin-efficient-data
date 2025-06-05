"""
Cluster reduction utilities for selecting representative documents
"""

from typing import Dict, List
import logging


def select_representative_document(cluster_docs: List[Dict], strategy: str = "longest") -> int:
    """
    Select representative document from a cluster of duplicates

    Args:
        cluster_docs: List of document dictionaries in the cluster
        strategy: Selection strategy ("longest", "newest", "highest_quality")

    Returns:
        Index of the representative document in the cluster
    """
    if not cluster_docs:
        return 0

    if len(cluster_docs) == 1:
        return 0

    if strategy == "longest":
        return _select_longest_document(cluster_docs)
    elif strategy == "newest":
        return _select_newest_document(cluster_docs)
    elif strategy == "highest_quality":
        return _select_highest_quality_document(cluster_docs)
    else:
        logging.warning(f"Unknown strategy {strategy}, using 'longest'")
        return _select_longest_document(cluster_docs)


def _select_longest_document(cluster_docs: List[Dict]) -> int:
    """Select document with most tokens/characters"""
    max_length = 0
    best_idx = 0

    for idx, doc in enumerate(cluster_docs):
        text = doc.get('text', '')

        # Prefer token count if available, otherwise use character count
        if 'tokens' in doc and isinstance(doc['tokens'], list):
            length = len(doc['tokens'])
        else:
            length = len(text)

        if length > max_length:
            max_length = length
            best_idx = idx

    return best_idx


def _select_newest_document(cluster_docs: List[Dict]) -> int:
    """Select document with most recent timestamp"""
    newest_time = None
    best_idx = 0

    for idx, doc in enumerate(cluster_docs):
        timestamp = doc.get('timestamp')

        if timestamp is None:
            continue

        # Handle different timestamp formats
        try:
            if isinstance(timestamp, str):
                from datetime import datetime
                # Try common formats
                for fmt in ['%Y-%m-%d %H:%M:%S', '%Y-%m-%dT%H:%M:%S', '%Y-%m-%d']:
                    try:
                        parsed_time = datetime.strptime(timestamp, fmt)
                        break
                    except ValueError:
                        continue
                else:
                    continue
            elif isinstance(timestamp, (int, float)):
                from datetime import datetime
                parsed_time = datetime.fromtimestamp(timestamp)
            else:
                continue

            if newest_time is None or parsed_time > newest_time:
                newest_time = parsed_time
                best_idx = idx

        except Exception:
            continue

    # If no valid timestamps found, fall back to longest
    if newest_time is None:
        return _select_longest_document(cluster_docs)

    return best_idx


def _select_highest_quality_document(cluster_docs: List[Dict]) -> int:
    """Select document with highest quality score"""
    best_score = -1
    best_idx = 0

    for idx, doc in enumerate(cluster_docs):
        score = _calculate_quality_score(doc)

        if score > best_score:
            best_score = score
            best_idx = idx

    return best_idx


def _calculate_quality_score(doc: Dict) -> float:
    """
    Calculate quality score for a document

    Factors considered:
    - Text length (longer is generally better)
    - Source reliability (if available)
    - Language quality indicators
    - Structural completeness
    """
    text = doc.get('text', '')
    score = 0.0

    # Length factor (normalized)
    text_length = len(text)
    score += min(text_length / 1000, 1.0) * 0.3

    # Source quality (if available)
    source = doc.get('source', '').lower()
    source_scores = {
        'wikipedia': 0.9,
        'news': 0.8,
        'book': 0.8,
        'academic': 0.9,
        'government': 0.7,
        'social': 0.3,
        'web': 0.4,
        'forum': 0.2
    }

    for source_type, source_score in source_scores.items():
        if source_type in source:
            score += source_score * 0.2
            break
    else:
        score += 0.1  # Default source score

    # Language quality indicators
    if text:
        # Check for proper sentence structure
        sentence_endings = text.count('.') + text.count('!') + text.count('?')
        avg_sentence_length = text_length / max(sentence_endings, 1)

        # Prefer moderate sentence lengths (not too short, not too long)
        if 20 <= avg_sentence_length <= 100:
            score += 0.2
        elif 10 <= avg_sentence_length <= 150:
            score += 0.1

        # Check for Korean content (basic heuristic)
        korean_chars = sum(1 for c in text if '\uac00' <= c <= '\ud7af')
        korean_ratio = korean_chars / max(text_length, 1)
        score += korean_ratio * 0.2

        # Penalize excessive repetition
        words = text.split()
        if len(words) > 10:
            unique_words = len(set(words))
            word_diversity = unique_words / len(words)
            score += word_diversity * 0.1

    # Metadata completeness
    metadata_fields = ['source', 'domain', 'lang', 'tokens']
    completeness = sum(1 for field in metadata_fields if field in doc and doc[field])
    score += (completeness / len(metadata_fields)) * 0.1

    return score


def analyze_cluster_statistics(clusters: List[List[Dict]]) -> Dict:
    """
    Analyze statistics about duplicate clusters

    Args:
        clusters: List of document clusters

    Returns:
        Dictionary with cluster statistics
    """
    if not clusters:
        return {}

    cluster_sizes = [len(cluster) for cluster in clusters]

    stats = {
        'total_clusters': len(clusters),
        'total_documents_in_clusters': sum(cluster_sizes),
        'avg_cluster_size': sum(cluster_sizes) / len(clusters),
        'max_cluster_size': max(cluster_sizes),
        'min_cluster_size': min(cluster_sizes),
        'cluster_size_distribution': {
            'size_2': sum(1 for size in cluster_sizes if size == 2),
            'size_3_5': sum(1 for size in cluster_sizes if 3 <= size <= 5),
            'size_6_10': sum(1 for size in cluster_sizes if 6 <= size <= 10),
            'size_10_plus': sum(1 for size in cluster_sizes if size > 10),
        }
    }

    return stats
