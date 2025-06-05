"""Benchmark pandas loading speed between Parquet and JSONL files."""

from __future__ import annotations

import argparse
from pathlib import Path
from time import perf_counter

import pytest

pytest.importorskip("pandas")

import pandas as pd
try:
    import torch  # noqa: F401
except Exception:
    pytest.skip("torch not available", allow_module_level=True)
from format.to_parquet import (
    convert_jsonl_to_parquet,
    benchmark_dataloader_speed,
)


def _time_read(func, path: Path, **kwargs) -> tuple[float, int]:
    """Return time taken to read a file and the resulting row count."""
    start = perf_counter()
    df = func(path, **kwargs)
    elapsed = perf_counter() - start
    return elapsed, len(df)


def benchmark(parquet_path: Path, jsonl_path: Path) -> None:
    """Measure loading speed for Parquet and JSONL files."""
    pq_time, pq_rows = _time_read(pd.read_parquet, parquet_path)
    jl_time, jl_rows = _time_read(pd.read_json, jsonl_path, lines=True)

    print(f"Parquet\t{pq_rows} rows\t{pq_time:.4f}s")
    print(f"JSONL\t{jl_rows} rows\t{jl_time:.4f}s")


def parse_args() -> argparse.Namespace:
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(
        description="Measure pandas loading speed between Parquet and JSONL files."
    )
    parser.add_argument("--parquet", type=Path, required=True, help="Parquet file path")
    parser.add_argument("--jsonl", type=Path, required=True, help="JSONL file path")
    return parser.parse_args()


def test_dataloader_benchmark(tmp_path) -> None:
    """Run the DataLoader benchmark on tiny sample files."""
    jsonl = tmp_path / "sample.jsonl"
    jsonl.write_text('{"text":"a","tokens":["a"]}\n{"text":"b","tokens":["b"]}\n', encoding="utf-8")
    parquet = tmp_path / "sample.parquet"
    config = {"schema": {"required_columns": ["text", "tokens"], "column_types": {"text": "string", "tokens": "list[string]"}}}
    convert_jsonl_to_parquet(str(jsonl), str(parquet), config, batch_size=1)

    results = benchmark_dataloader_speed(str(jsonl), str(parquet), batch_size=1, num_samples=2)
    assert results["parquet_time_ms"] >= 0


if __name__ == "__main__":
    args = parse_args()
    benchmark(args.parquet, args.jsonl)

