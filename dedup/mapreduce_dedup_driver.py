#!/usr/bin/env python3
"""Simple MapReduce-style deduplication driver."""

from __future__ import annotations

import argparse
import json
from multiprocessing import Pool
from pathlib import Path
from typing import Dict, List

from .slimpajama_dedup import (
    load_config,
    build_minhash_index,
    find_duplicate_clusters,
    deduplicate_documents,
)


def _process_chunk(args: tuple[List[str], Dict]) -> List[Dict]:
    """Process a single data chunk and return deduplicated documents."""

    lines, config = args
    docs = [json.loads(line) for line in lines if line.strip()]
    lsh, minhashes = build_minhash_index(docs, config)
    clusters = find_duplicate_clusters(lsh, minhashes)
    deduped, _ = deduplicate_documents(docs, clusters)
    return deduped


def run_dedup_mapreduce(
    input_path: str,
    output_path: str,
    config_path: str,
    workers: int = 2,
    chunk_size: int = 100,
) -> None:
    """Run the deduplication pipeline using a simple MapReduce approach."""

    config = load_config(config_path)
    lines = Path(input_path).read_text(encoding="utf-8").splitlines()
    chunks = [
        lines[i:i + chunk_size] for i in range(0, len(lines), chunk_size)
    ]

    with Pool(processes=workers) as pool:
        results = pool.map(
            _process_chunk,
            [(chunk, config) for chunk in chunks],
        )

    deduped_docs = [doc for part in results for doc in part]
    with open(output_path, "w", encoding="utf-8") as out_f:
        for doc in deduped_docs:
            out_f.write(json.dumps(doc, ensure_ascii=False) + "\n")


def main() -> None:
    parser = argparse.ArgumentParser(description="MapReduce dedup driver")
    parser.add_argument("--config", default="configs/dataset_config.yaml")
    parser.add_argument("--input", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--workers", type=int, default=2)
    parser.add_argument("--chunk-size", type=int, default=100)
    args = parser.parse_args()

    run_dedup_mapreduce(
        args.input,
        args.output,
        args.config,
        args.workers,
        args.chunk_size,
    )


if __name__ == "__main__":  # pragma: no cover - CLI
    main()
