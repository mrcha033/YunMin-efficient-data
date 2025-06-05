"""Benchmark data loading speed between Parquet and JSONL."""

from time import perf_counter
from pathlib import Path


def benchmark(parquet_path: Path, jsonl_path: Path) -> None:
    """Run a simple loading benchmark."""
    # TODO: implement benchmark logic using pandas
    start = perf_counter()
    _ = parquet_path, jsonl_path
    end = perf_counter()
    print(f"Benchmark completed in {end - start:.2f}s")


if __name__ == "__main__":
    benchmark(Path("data/sample.parquet"), Path("data/sample.jsonl"))
