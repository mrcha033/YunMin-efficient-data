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

from .minhash_utils import create_minhash, tokenize_ngrams
from .cluster_reduction import select_representative_document


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


def validate_jsonl_file(file_path: str, sample_size: int = 100) -> Tuple[bool, int, List[str]]:
    """
    Validate JSONL file format and return sample documents
    
    Args:
        file_path: Path to JSONL file
        sample_size: Number of samples to return for inspection
        
    Returns:
        Tuple of (is_valid, total_lines, sample_documents)
    """
    logger = logging.getLogger(__name__)
    
    try:
        total_lines = 0
        samples = []
        invalid_lines = 0
        
        with open(file_path, 'r', encoding='utf-8') as f:
            for line_num, line in enumerate(f, 1):
                line = line.strip()
                if not line:
                    continue
                    
                try:
                    doc = json.loads(line)
                    total_lines += 1
                    
                    # Collect samples
                    if len(samples) < sample_size:
                        samples.append(doc.get('text', ''))
                        
                except json.JSONDecodeError:
                    invalid_lines += 1
                    if invalid_lines < 10:  # Log first 10 errors
                        logger.warning(f"Invalid JSON at line {line_num}: {line[:100]}...")
        
        is_valid = invalid_lines / max(total_lines, 1) < 0.01  # Less than 1% invalid
        logger.info(f"File {file_path}: {total_lines} valid lines, {invalid_lines} invalid lines")
        
        return is_valid, total_lines, samples
        
    except Exception as e:
        logger.error(f"Error validating file {file_path}: {e}")
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
    
    # Initialize LSH
    lsh = MinHashLSH(threshold=threshold, num_perm=num_perm)
    minhashes = {}
    
    logger.info(f"Building MinHash LSH index with {num_perm} permutations, threshold={threshold}")
    
    for doc_id, doc in enumerate(tqdm(documents, desc="Creating MinHashes")):
        text = preprocess_text(doc.get('text', ''))
        
        if len(text.strip()) < 10:  # Skip very short texts
            continue
            
        # Create n-grams and MinHash
        ngrams = tokenize_ngrams(text, ngram_size)
        if len(ngrams) < 5:  # Skip texts with too few n-grams
            continue
            
        minhash = create_minhash(ngrams, num_perm)
        minhashes[str(doc_id)] = minhash
        
        # Add to LSH index
        lsh.insert(str(doc_id), minhash)
    
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
    parser = argparse.ArgumentParser(description="SlimPajama-based deduplication")
    parser.add_argument("--config", default="configs/dataset_config.yaml", help="Configuration file")
    parser.add_argument("--input", required=True, help="Input JSONL file path")
    parser.add_argument("--output", required=True, help="Output JSONL file path")
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
        
        # Validate input file
        logger.info(f"Validating input file: {args.input}")
        is_valid, total_lines, samples = validate_jsonl_file(args.input)
        
        if not is_valid:
            logger.error("Input file validation failed")
            return
        
        logger.info(f"Input file is valid with {total_lines} documents")
        
        # Load documents
        logger.info("Loading documents...")
        documents = []
        with open(args.input, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if line:
                    try:
                        doc = json.loads(line)
                        documents.append(doc)
                    except json.JSONDecodeError:
                        continue
        
        logger.info(f"Loaded {len(documents)} documents")
        
        # Build MinHash index
        lsh, minhashes = build_minhash_index(documents, config)
        
        # Find duplicate clusters
        duplicate_clusters = find_duplicate_clusters(lsh, minhashes)
        
        # Deduplicate
        deduplicated_docs, stats = deduplicate_documents(documents, duplicate_clusters)
        
        # Save results
        os.makedirs(os.path.dirname(args.output), exist_ok=True)
        
        with open(args.output, 'w', encoding='utf-8') as f:
            for doc in deduplicated_docs:
                f.write(json.dumps(doc, ensure_ascii=False) + '\n')
        
        # Save statistics
        stats_file = args.output.replace('.jsonl', '_stats.json')
        with open(stats_file, 'w', encoding='utf-8') as f:
            json.dump(stats, f, indent=2, ensure_ascii=False)
        
        end_time = time.time()
        processing_time = end_time - start_time
        
        logger.info(f"Deduplication completed in {processing_time:.2f} seconds")
        logger.info(f"Results saved to: {args.output}")
        logger.info(f"Statistics saved to: {stats_file}")
        
    except Exception as e:
        logger.error(f"Deduplication failed: {e}", exc_info=True)
        raise


if __name__ == "__main__":
    main() 