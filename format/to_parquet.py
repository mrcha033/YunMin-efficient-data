#!/usr/bin/env python3
"""
JSONL to Parquet conversion for YunMin-EfficientData
Implements Youmu-based columnar format for efficient data loading.
"""

import json
import logging
import os
import time
from typing import Dict, List

import psutil
try:  # pragma: no cover - torch may be unavailable
    import torch
    from torch.utils.data import Dataset, DataLoader
except Exception:  # pragma: no cover - fallback stubs
    torch = None

    class Dataset:  # type: ignore
        pass

    def DataLoader(*args, **kwargs):  # type: ignore
        raise ImportError("torch is required for DataLoader benchmark")
import argparse

import pyarrow as pa
import pyarrow.parquet as pq
import pyarrow.json as pj

try:
    from tqdm import tqdm
except Exception:  # pragma: no cover - fallback if tqdm missing
    class DummyTqdm(list):  # pragma: no cover - simple fallback
        def __init__(self, iterable=None, **kwargs):
            super().__init__(iterable or [])

        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc_val, exc_tb):
            return False

        def update(self, n=1) -> None:  # pragma: no cover - no-op
            pass

    def tqdm(iterable=None, **kwargs):
        return DummyTqdm(iterable, **kwargs)
try:
    import yaml
except Exception:  # pragma: no cover - fallback if PyYAML missing
    yaml = None  # type: ignore

from .parquet_utils import create_schema, validate_parquet_file
from utils.cloud_storage import get_storage_client


def setup_logging():
    """Setup logging configuration"""
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler('logs/format_conversion.log'),
            logging.StreamHandler()
        ]
    )
    return logging.getLogger(__name__)


def load_config(config_path: str) -> Dict:
    """Load configuration from YAML file"""
    if yaml is None:
        raise ImportError("PyYAML is required for configuration loading")
    with open(config_path, 'r', encoding='utf-8') as f:
        return yaml.safe_load(f)


def load_jsonl_batch_from_cloud(storage_client, file_path: str, batch_size: int = 1000, start_line: int = 0) -> List[Dict]:
    """
    Load a batch of documents from JSONL file in cloud storage

    Args:
        storage_client: Cloud storage client
        file_path: Path to JSONL file in cloud storage
        batch_size: Number of documents to load
        start_line: Starting line number

    Returns:
        List of document dictionaries
    """
    documents = []
    current_line = 0

    # Read all documents and skip to start line
    for doc in storage_client.read_jsonl_file(file_path):
        if current_line < start_line:
            current_line += 1
            continue

        if len(documents) >= batch_size:
            break

        documents.append(doc)
        current_line += 1

    return documents


def load_jsonl_batch(file_path: str, batch_size: int = 1000, start_line: int = 0) -> List[Dict]:
    """Load a batch of JSONL documents from a local file."""
    docs: List[Dict] = []
    with open(file_path, "r", encoding="utf-8") as fh:
        for i, line in enumerate(fh):
            if i < start_line:
                continue
            if len(docs) >= batch_size:
                break
            line = line.strip()
            if not line:
                continue
            try:
                docs.append(json.loads(line))
            except json.JSONDecodeError:
                continue
    return docs


def clean_and_validate_documents(documents: List[Dict], schema_config: Dict) -> List[Dict]:
    """
    Clean and validate documents according to schema

    Args:
        documents: List of document dictionaries
        schema_config: Schema configuration from config file

    Returns:
        List of cleaned and validated documents
    """
    required_columns = schema_config.get('required_columns', [])
    column_types = schema_config.get('column_types', {})

    cleaned_docs = []

    for doc in documents:
        # Check required columns
        if not all(col in doc for col in required_columns):
            continue

        # Create cleaned document with only required columns
        cleaned_doc = {}

        for col in required_columns:
            value = doc.get(col)

            # Handle missing values
            if value is None:
                if column_types.get(col) == 'string':
                    value = ''
                elif column_types.get(col) == 'list[string]':
                    value = []
                else:
                    value = ''

            # Type validation and conversion
            if column_types.get(col) == 'string' and not isinstance(value, str):
                value = str(value)
            elif column_types.get(col) == 'list[string]' and not isinstance(value, list):
                if isinstance(value, str):
                    value = [value]
                else:
                    value = []

            cleaned_doc[col] = value

        # Skip documents with empty text
        if not cleaned_doc.get('text', '').strip():
            continue

        cleaned_docs.append(cleaned_doc)

    return cleaned_docs


def convert_to_parquet_batch(documents: List[Dict], schema: pa.Schema) -> pa.Table:
    """
    Convert a batch of documents to PyArrow Table

    Args:
        documents: List of document dictionaries
        schema: PyArrow schema

    Returns:
        PyArrow Table
    """
    if not documents:
        return pa.table({}, schema=schema)

    # Create arrays for each column
    arrays = {}

    for field in schema:
        column_name = field.name
        values = [doc.get(column_name) for doc in documents]

        if field.type == pa.string():
            arrays[column_name] = pa.array(values, type=pa.string())
        elif field.type == pa.list_(pa.string()):
            arrays[column_name] = pa.array(values, type=pa.list_(pa.string()))
        else:
            arrays[column_name] = pa.array(values)

    return pa.table(arrays, schema=schema)


class JSONLDataset(Dataset):
    """Dataset for reading JSONL files."""

    def __init__(self, path: str, limit: int | None = None) -> None:
        self.data: List[Dict] = []
        with open(path, "r", encoding="utf-8") as fh:
            for i, line in enumerate(fh):
                if limit is not None and i >= limit:
                    break
                line = line.strip()
                if not line:
                    continue
                try:
                    self.data.append(json.loads(line))
                except json.JSONDecodeError:
                    continue

    def __len__(self) -> int:  # pragma: no cover - trivial
        return len(self.data)

    def __getitem__(self, idx: int) -> Dict:
        return self.data[idx]


class ParquetDataset(Dataset):
    """Dataset for reading Parquet files."""

    def __init__(self, path: str, columns: List[str] | None = None) -> None:
        table = pq.read_table(path, columns=columns)
        self.data = table.to_pydict()
        self.columns = list(table.column_names)
        self.length = table.num_rows

    def __len__(self) -> int:  # pragma: no cover - trivial
        return self.length

    def __getitem__(self, idx: int) -> Dict:
        return {col: self.data[col][idx] for col in self.columns}


def get_total_lines(file_path: str) -> int:
    """Get total number of lines in a file"""
    with open(file_path, 'r', encoding='utf-8') as f:
        return sum(1 for _ in f)


def convert_jsonl_to_parquet(
    input_file: str,
    output_file: str,
    config: Dict,
    batch_size: int = 1000,
    compression: str = "brotli",
) -> None:
    """
    Convert JSONL file to Parquet format
    using a cloud storage client for reading

    Args:
        input_file: Path to input JSONL file
        output_file: Path to output Parquet file
        config: Configuration dictionary
        batch_size: Batch size for processing
    """
    logger = logging.getLogger(__name__)

    # Get schema configuration
    schema_config = config.get('schema', {})

    # Create PyArrow schema
    schema = create_schema(schema_config)
    logger.info(f"Created schema: {schema}")

    # Prepare reader and writer
    block_size = max(batch_size, 1) * 1024
    read_opts = pj.ReadOptions(block_size=block_size)
    parse_opts = pj.ParseOptions(explicit_schema=schema)
    os.makedirs(os.path.dirname(output_file), exist_ok=True)
    # Column-level compression: text with Brotli, tokens with Zstd
    compression_map = {"text": "brotli", "tokens": "zstd"}
    writer = pq.ParquetWriter(output_file, schema, compression=compression_map)

    with tqdm(total=total_lines, desc="Converting to Parquet") as pbar:
        while processed_lines < total_lines:
            # Load batch
            documents = load_jsonl_batch(
                input_file, batch_size, processed_lines)

            if not documents:
                break

    with pj.open_json(
        input_file,
        read_options=read_opts,
        parse_options=parse_opts,
    ) as reader, pq.ParquetWriter(
        output_file,
        schema,
        compression=compression,
    ) as writer:
        for record_batch in reader:
            writer.write_batch(record_batch)

    logger.info(f"Saved Parquet file: {output_file}")

    schema_path = os.path.join(os.path.dirname(output_file), "schema.txt")
    with open(schema_path, "w", encoding="utf-8") as f:
        for field in schema:
            f.write(f"{field.name}:{field.type}\n")

    if validate_parquet_file(output_file):
        logger.info("Parquet file validation passed")
    else:
        logger.error("Parquet file validation failed")


def benchmark_loading_speed(jsonl_file: str, parquet_file: str, batch_size: int = 16) -> Dict:
    """
    Benchmark loading speed between JSONL and Parquet formats

    Args:
        jsonl_file: Path to JSONL file
        parquet_file: Path to Parquet file
        batch_size: Batch size for loading

    Returns:
        Dictionary with benchmark results
    """
    logger = logging.getLogger(__name__)

    results = {
        'jsonl': {'time': 0, 'memory': 0},
        'parquet': {'time': 0, 'memory': 0}
    }

    # Benchmark JSONL loading
    try:
        import psutil
        import tracemalloc

        # JSONL benchmark
        tracemalloc.start()
        start_time = time.time()

        documents = []
        with open(jsonl_file, 'r', encoding='utf-8') as f:
            for i, line in enumerate(f):
                if i >= batch_size:
                    break
                line = line.strip()
                if line:
                    try:
                        doc = json.loads(line)
                        documents.append(doc)
                    except json.JSONDecodeError:
                        continue

        jsonl_time = time.time() - start_time
        _, jsonl_memory = tracemalloc.get_traced_memory()
        tracemalloc.stop()

        results['jsonl']['time'] = jsonl_time * 1000  # Convert to ms
        results['jsonl']['memory'] = jsonl_memory / \
            1024 / 1024  # Convert to MB

        logger.info(
            f"JSONL loading: {jsonl_time*1000:.2f}ms, {jsonl_memory/1024/1024:.2f}MB")

    except Exception as e:
        logger.error(f"JSONL benchmark failed: {e}")

    # Benchmark Parquet loading
    try:
        tracemalloc.start()
        start_time = time.time()

        # Load only required columns
        table = pq.read_table(parquet_file, columns=['text', 'tokens'])
        df = table.to_pandas().head(batch_size)

        parquet_time = time.time() - start_time
        _, parquet_memory = tracemalloc.get_traced_memory()
        tracemalloc.stop()

        results['parquet']['time'] = parquet_time * 1000  # Convert to ms
        results['parquet']['memory'] = parquet_memory / \
            1024 / 1024  # Convert to MB

        logger.info(
            f"Parquet loading: {parquet_time*1000:.2f}ms, {parquet_memory/1024/1024:.2f}MB")

    except Exception as e:
        logger.error(f"Parquet benchmark failed: {e}")

    # Calculate improvements
    if results['jsonl']['time'] > 0:
        results['time_improvement'] = results['jsonl']['time'] / \
            results['parquet']['time']
    else:
        results['time_improvement'] = 0

    if results['jsonl']['memory'] > 0:
        results['memory_improvement'] = results['jsonl']['memory'] / \
            results['parquet']['memory']
    else:
        results['memory_improvement'] = 0

    return results


def benchmark_dataloader_speed(
    jsonl_file: str,
    parquet_file: str,
    batch_size: int = 16,
    num_samples: int = 32,
    csv_path: str = "benchmark/io_speed.csv",
) -> Dict:
    """Benchmark DataLoader speed between JSONL and Parquet files."""
    logger = logging.getLogger(__name__)

    def _measure(dataset: Dataset) -> tuple[float, float]:
        loader = DataLoader(dataset, batch_size=batch_size)
        process = psutil.Process(os.getpid())
        start_mem = process.memory_info().rss
        start = time.perf_counter()
        for _ in loader:
            pass
        elapsed = time.perf_counter() - start
        mem_usage = (process.memory_info().rss - start_mem) / 1024 / 1024
        return elapsed * 1000, mem_usage

    json_ds = JSONLDataset(jsonl_file, limit=num_samples)
    parquet_ds = ParquetDataset(parquet_file, columns=["text", "tokens"])

    json_time, json_mem = _measure(json_ds)
    pq_time, pq_mem = _measure(parquet_ds)

    results = {
        "jsonl_time_ms": json_time,
        "jsonl_memory_mb": json_mem,
        "parquet_time_ms": pq_time,
        "parquet_memory_mb": pq_mem,
        "time_improvement": json_time / pq_time if pq_time else 0,
        "memory_improvement": json_mem / pq_mem if pq_mem else 0,
    }

    os.makedirs(os.path.dirname(csv_path), exist_ok=True)
    write_header = not os.path.exists(csv_path)
    import csv

    with open(csv_path, "a", newline="", encoding="utf-8") as csv_f:
        writer = csv.DictWriter(csv_f, fieldnames=list(results.keys()))
        if write_header:
            writer.writeheader()
        writer.writerow(results)

    logger.info(
        "DataLoader benchmark - JSONL: %.2fms %.2fMB, Parquet: %.2fms %.2fMB",
        json_time,
        json_mem,
        pq_time,
        pq_mem,
    )
    return results


def main():
    parser = argparse.ArgumentParser(description="JSONL to Parquet conversion")
    parser.add_argument(
        "--config", default="configs/dataset_config.yaml", help="Configuration file")
    parser.add_argument("--input", required=True, help="Input JSONL file path")
    parser.add_argument("--domain", required=True, help="Domain name")
    parser.add_argument("--batch-size", type=int,
                        default=1000, help="Batch size for processing")
    parser.add_argument(
        "--compression",
        choices=["brotli", "zstd"],
        default="brotli",
        help="Compression codec",
    )
    parser.add_argument("--benchmark", action="store_true",
                        help="Run loading speed benchmark")

    args = parser.parse_args()

    # Setup logging
    logger = setup_logging()

    start_time = time.time()

    try:
        # Load configuration
        config = load_config(args.config)
        logger.info(f"Loaded configuration from {args.config}")

        output_path = os.path.join("data", "parquet", f"{args.domain}.parquet")

        # Convert JSONL to Parquet
        logger.info(f"Converting {args.input} to {output_path}")
        convert_jsonl_to_parquet(
            args.input,
            output_path,
            config,
            args.batch_size,
            compression=args.compression,
        )

        # Run benchmark if requested
        if args.benchmark and os.path.exists(output_path):
            logger.info("Running loading speed benchmark...")
            benchmark_results = benchmark_dataloader_speed(
                args.input, args.output, batch_size=args.batch_size
            )

            benchmark_file = args.output.replace(".parquet", "_benchmark.json")
            with open(benchmark_file, "w", encoding="utf-8") as f:
                json.dump(benchmark_results, f, indent=2)

            logger.info(f"Benchmark results saved to: {benchmark_file}")
            logger.info(
                "Loading speed improvement: %.2fx",
                benchmark_results.get("time_improvement", 0),
            )
            logger.info(
                "Memory usage improvement: %.2fx",
                benchmark_results.get("memory_improvement", 0),
            )

        end_time = time.time()
        processing_time = end_time - start_time

        logger.info(f"Conversion completed in {processing_time:.2f} seconds")

    except Exception as e:
        logger.error(f"Conversion failed: {e}", exc_info=True)
        raise


if __name__ == "__main__":
    main()
