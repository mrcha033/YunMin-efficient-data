#!/usr/bin/env python3
"""Ray-based distributed deduplication driver."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Dict, List, Tuple

import ray

from .slimpajama_dedup import (
    load_config,
    build_minhash_index,
    find_duplicate_clusters,
    deduplicate_documents,
)


@ray.remote
def _process_chunk(lines: List[str], config: Dict) -> Tuple[List[Dict], List[List[str]], Dict]:
    """Process a data chunk and return deduped documents and stats."""
    docs = [json.loads(line) for line in lines if line.strip()]
    lsh, minhashes = build_minhash_index(docs, config)
    clusters = find_duplicate_clusters(lsh, minhashes)
    deduped, stats = deduplicate_documents(docs, clusters)
    candidate_clusters = [list(cluster) for cluster in clusters]
    return deduped, candidate_clusters, stats


def run_dedup_ray(
    input_path: str,
    output_path: str,
    log_csv: str,
    candidates_path: str,
    config_path: str,
    num_workers: int = 2,
    chunk_size: int = 100,
    local: bool = False,
) -> None:
    """Run deduplication using Ray for parallel processing."""
    config = load_config(config_path)
    lines = Path(input_path).read_text(encoding="utf-8").splitlines()
    chunks = [lines[i : i + chunk_size] for i in range(0, len(lines), chunk_size)]

    ray.init(local_mode=local, num_cpus=num_workers, ignore_reinit_error=True)
    futures = [_process_chunk.remote(chunk, config) for chunk in chunks]
    results = ray.get(futures)
    ray.shutdown()

    deduped_docs: List[Dict] = []
    all_candidates: List[List[str]] = []
    stats_total = {
        "original_count": 0,
        "deduplicated_count": 0,
        "removed_count": 0,
        "duplicate_clusters": 0,
    }

    for docs, candidates, stats in results:
        deduped_docs.extend(docs)
        all_candidates.extend(candidates)
        for key in stats_total:
            stats_total[key] += stats.get(key, 0)

    stats_total["deduplication_rate"] = (
        stats_total["removed_count"] / stats_total["original_count"]
        if stats_total["original_count"]
        else 0
    )

    with open(output_path, "w", encoding="utf-8") as out_f:
        for doc in deduped_docs:
            out_f.write(json.dumps(doc, ensure_ascii=False) + "\n")

    with open(log_csv, "w", encoding="utf-8") as log_f:
        headers = [
            "original_count",
            "deduplicated_count",
            "removed_count",
            "duplicate_clusters",
            "deduplication_rate",
        ]
        log_f.write(",".join(headers) + "\n")
        log_f.write(",".join(str(stats_total[h]) for h in headers) + "\n")

    with open(candidates_path, "w", encoding="utf-8") as cand_f:
        json.dump(all_candidates, cand_f, ensure_ascii=False, indent=2)


def main() -> None:
    parser = argparse.ArgumentParser(description="Distributed deduplication with Ray")
    parser.add_argument("--config", default="configs/dataset_config.yaml")
    parser.add_argument("--input", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--log-csv", required=True)
    parser.add_argument("--candidates", required=True)
    parser.add_argument("--num-workers", type=int, default=2)
    parser.add_argument("--chunk-size", type=int, default=100)
    parser.add_argument("--local", action="store_true", help="Run Ray in local mode")
    args = parser.parse_args()

    run_dedup_ray(
        args.input,
        args.output,
        args.log_csv,
        args.candidates,
        args.config,
        args.num_workers,
        args.chunk_size,
        args.local,
    )


if __name__ == "__main__":  # pragma: no cover - CLI
    main()
