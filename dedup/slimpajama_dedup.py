#!/usr/bin/env python3
"""
SlimPajama-based deduplication for YunMin-EfficientData
Implements MinHash + LSH for near-duplicate detection and removal.
"""

import json
import logging
import os
import time
from pathlib import Path
from typing import Dict, List, Set, Tuple
import argparse

import pandas as pd
from datasketch import MinHash, MinHashLSH
from tqdm import tqdm
import yaml

from .minhash_utils import (
    create_minhash,
    tokenize_ngrams,
    tokenize_jamo_ngrams,
)
import redis
from .cluster_reduction import select_representative_document
from utils.cloud_storage import get_storage_client
from utils.data_utils import (
    validate_jsonl_format,
    validate_json,
    normalize_document,
)


def setup_logging():
    """Setup logging configuration"""
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler('logs/dedup.log'),
            logging.StreamHandler()
        ]
    )
    return logging.getLogger(__name__)


def load_config(config_path: str) -> Dict:
    """Load configuration from YAML file"""
    with open(config_path, 'r', encoding='utf-8') as f:
        return yaml.safe_load(f)


def validate_cloud_jsonl_file(storage_client, file_path: str, sample_size: int = 100) -> Tuple[bool, int, List[str]]:
    """
    Validate JSONL file format from cloud storage and return sample documents

    Args:
        storage_client: Cloud storage client
        file_path: Path to JSONL file in cloud storage
        sample_size: Number of samples to return for inspection

    Returns:
        Tuple of (is_valid, total_lines, sample_documents)
    """
    logger = logging.getLogger(__name__)

    try:
        # Read file content from cloud storage
        file_content = storage_client.read_text_file(file_path)

        # Validate using the utility function
        is_valid, validation_info = validate_jsonl_format(file_content, sample_size)

        # Extract samples for compatibility
        samples = [doc.get('text', '') for doc in validation_info['sample_documents']]

        logger.info(f"Cloud file {file_path}: {validation_info['valid_lines']} valid lines, "
                   f"{validation_info['invalid_lines']} invalid lines")

        return is_valid, validation_info['valid_lines'], samples

    except Exception as e:
        logger.error(f"Error validating cloud file {file_path}: {e}")
        return False, 0, []


def preprocess_text(text: str) -> str:
    """
    Preprocess text for deduplication

    Args:
        text: Input text

    Returns:
        Preprocessed text
    """
    import unicodedata

    # Normalize unicode
    text = unicodedata.normalize('NFKC', text)

    # Remove extra whitespace
    text = ' '.join(text.split())

    # Remove common noise patterns (optional)
    # You can add more preprocessing here

    return text.strip()


def build_minhash_index(documents: List[Dict], config: Dict) -> Tuple[MinHashLSH, Dict[str, MinHash]]:
    """
    Build MinHash LSH index for duplicate detection

    Args:
        documents: List of document dictionaries
        config: Configuration dictionary

    Returns:
        Tuple of (LSH index, document_id -> MinHash mapping)
    """
    logger = logging.getLogger(__name__)

    # Configuration
    num_perm = config.get('minhash_permutations', 128)
    threshold = config.get('similarity_threshold', 0.8)
    ngram_size = config.get('ngram_size', 5)
    jamo_ngram_size = config.get('jamo_ngram_size', 3)

    redis_cfg = config.get('redis', {})
    storage_config = {
        'type': 'redis',
        'basename': redis_cfg.get('prefix', 'dedup').encode(),
        'redis': {
            'host': redis_cfg.get('host', 'localhost'),
            'port': int(redis_cfg.get('port', 6379)),
        },
    }

    # Initialize LSH backed by Redis
    lsh = MinHashLSH(threshold=threshold, num_perm=num_perm, storage_config=storage_config)
    minhashes: Dict[str, MinHash] = {}
    redis_client = redis.Redis(
        host=storage_config['redis']['host'],
        port=storage_config['redis']['port'],
    )

    logger.info(f"Building MinHash LSH index with {num_perm} permutations, threshold={threshold}")

    for doc_id, doc in enumerate(tqdm(documents, desc="Creating MinHashes")):
        text = preprocess_text(doc.get('text', ''))

        if len(text.strip()) < 10:  # Skip very short texts
            continue

        # Create n-grams (word and jamo) and MinHash
        word_ngrams = tokenize_ngrams(text, ngram_size)
        jamo_ngrams = tokenize_jamo_ngrams(text, jamo_ngram_size)
        combined = word_ngrams + jamo_ngrams
        if len(combined) < 5:
            continue

        minhash = create_minhash(combined, num_perm)
        minhashes[str(doc_id)] = minhash

        # Add to LSH index
        lsh.insert(str(doc_id), minhash)

        # Store signature for later inspection
        redis_client.set(
            f"{storage_config['basename'].decode()}:sig:{doc_id}",
            json.dumps(list(minhash.digest())),
        )

    logger.info(f"Created MinHash index with {len(minhashes)} documents")
    return lsh, minhashes


def find_duplicate_clusters(lsh: MinHashLSH, minhashes: Dict[str, MinHash]) -> List[Set[str]]:
    """
    Find clusters of duplicate documents

    Args:
        lsh: MinHash LSH index
        minhashes: Document ID to MinHash mapping

    Returns:
        List of document ID clusters
    """
    logger = logging.getLogger(__name__)

    clusters = []
    processed = set()

    for doc_id in tqdm(minhashes.keys(), desc="Finding duplicates"):
        if doc_id in processed:
            continue

        # Find similar documents
        candidates = lsh.query(minhashes[doc_id])

        if len(candidates) > 1:  # Found duplicates
            cluster = set(candidates)
            clusters.append(cluster)
            processed.update(cluster)
        else:
            processed.add(doc_id)

    logger.info(f"Found {len(clusters)} duplicate clusters")
    return clusters


def deduplicate_documents(documents: List[Dict], duplicate_clusters: List[Set[str]]) -> Tuple[List[Dict], Dict]:
    """
    Remove duplicates by selecting representative documents from each cluster

    Args:
        documents: Original document list
        duplicate_clusters: List of duplicate document ID clusters

    Returns:
        Tuple of (deduplicated documents, dedup statistics)
    """
    logger = logging.getLogger(__name__)

    # Create mapping of doc_id -> cluster_id
    doc_to_cluster = {}
    for cluster_id, cluster in enumerate(duplicate_clusters):
        for doc_id in cluster:
            doc_to_cluster[doc_id] = cluster_id

    # Select representative from each cluster
    representatives = set()
    for cluster in duplicate_clusters:
        cluster_docs = [documents[int(doc_id)] for doc_id in cluster if int(doc_id) < len(documents)]
        if cluster_docs:
            rep_idx = select_representative_document(cluster_docs)
            # Convert back to original document index
            original_indices = [int(doc_id) for doc_id in cluster if int(doc_id) < len(documents)]
            representatives.add(original_indices[rep_idx])

    # Keep non-duplicate documents and representatives
    deduplicated = []
    removed_count = 0

    for idx, doc in enumerate(documents):
        doc_id = str(idx)

        if doc_id in doc_to_cluster:
            # This document is part of a duplicate cluster
            if idx in representatives:
                deduplicated.append(doc)
            else:
                removed_count += 1
        else:
            # Not a duplicate, keep it
            deduplicated.append(doc)

    # Calculate statistics
    stats = {
        'original_count': len(documents),
        'deduplicated_count': len(deduplicated),
        'removed_count': removed_count,
        'duplicate_clusters': len(duplicate_clusters),
        'deduplication_rate': removed_count / len(documents) if documents else 0
    }

    logger.info(f"Deduplication complete: {stats['original_count']} → {stats['deduplicated_count']} "
                f"({stats['deduplication_rate']:.2%} reduction)")

    return deduplicated, stats


def main():
    parser = argparse.ArgumentParser(description="SlimPajama-based deduplication with cloud storage support")
    parser.add_argument("--config", default="configs/dataset_config.yaml", help="Configuration file")
    parser.add_argument("--input", required=True, help="Input JSONL file path (cloud storage path)")
    parser.add_argument("--output", required=True, help="Output JSONL file path (cloud storage path)")
    parser.add_argument("--log-file", help="Additional log file for this run")

    args = parser.parse_args()

    # Setup logging
    logger = setup_logging()
    if args.log_file:
        logger.addHandler(logging.FileHandler(args.log_file))

    start_time = time.time()

    try:
        # Load configuration
        config = load_config(args.config)
        logger.info(f"Loaded configuration from {args.config}")

        # Initialize cloud storage client
        storage_client = get_storage_client(config)
        logger.info(f"Initialized {storage_client.provider} storage client")

        # Validate input file
        logger.info(f"Validating cloud input file: {args.input}")
        is_valid, total_lines, samples = validate_cloud_jsonl_file(storage_client, args.input)

        if not is_valid:
            logger.error("Cloud input file validation failed")
            return

        logger.info(f"Cloud input file is valid with {total_lines} documents")

        # Stream and validate documents line by line
        logger.info("Streaming and validating documents...")
        required_fields = config.get("schema", {}).get("required_columns", ["text"])
        documents = []
        valid_lines: list[str] = []
        valid_count = 0
        invalid_count = 0
        for doc in storage_client.stream_jsonl(args.input):
            is_valid, err = validate_json(doc, required_fields)
            if is_valid:
                cleaned = normalize_document(doc)
                documents.append(cleaned)
                valid_lines.append(json.dumps(cleaned, ensure_ascii=False))
                valid_count += 1
            else:
                invalid_count += 1

        logger.info(
            "Validation finished: %d valid lines, %d invalid lines",
            valid_count,
            invalid_count,
        )

        # Save cleaned lines to dedup_ready
        dedup_ready_dir = config.get("paths", {}).get("dedup_ready", "data/dedup_ready/")
        ready_path = os.path.join(dedup_ready_dir, Path(args.input).name)
        ready_content = "\n".join(valid_lines)
        storage_client.write_text_file(ready_path, ready_content)

        # Save preview of first five documents
        preview_path = os.path.join(dedup_ready_dir, "sample_preview.json")
        storage_client.write_text_file(
            preview_path,
            json.dumps(documents[:5], ensure_ascii=False, indent=2),
        )

        # Build MinHash index
        lsh, minhashes = build_minhash_index(documents, config)

        # Find duplicate clusters
        duplicate_clusters = find_duplicate_clusters(lsh, minhashes)

        # Deduplicate
        deduplicated_docs, stats = deduplicate_documents(documents, duplicate_clusters)

        # Save results to cloud storage
        logger.info(f"Saving deduplicated results to cloud storage: {args.output}")

        # Create JSONL content
        jsonl_content = '\n'.join(json.dumps(doc, ensure_ascii=False) for doc in deduplicated_docs)

        # Upload to cloud storage
        success = storage_client.write_text_file(args.output, jsonl_content)
        if not success:
            raise Exception("Failed to save results to cloud storage")

        # Save statistics
        stats_path = args.output.replace('.jsonl', '_stats.json')
        stats_content = json.dumps(stats, indent=2, ensure_ascii=False)
        storage_client.write_text_file(stats_path, stats_content)

        end_time = time.time()
        processing_time = end_time - start_time

        logger.info(f"Deduplication completed in {processing_time:.2f} seconds")
        logger.info(f"Results saved to cloud storage: {args.output}")
        logger.info(f"Statistics saved to cloud storage: {stats_path}")

    except Exception as e:
        logger.error(f"Deduplication failed: {e}", exc_info=True)
        raise


if __name__ == "__main__":
    main()
