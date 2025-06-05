"""Placeholder tests for format module."""

import pytest

pytest.importorskip("pandas")
pytest.importorskip("pyarrow")

from format.to_parquet import (
    main as to_parquet_main,
    convert_jsonl_to_parquet,
    create_schema,
)
import pyarrow.parquet as pq

def test_to_parquet_exists() -> None:
    """Ensure conversion entrypoint exists."""
    assert callable(to_parquet_main)

def test_convert_jsonl_to_parquet(tmp_path) -> None:
    """Convert a tiny JSONL file and verify output."""
    sample = tmp_path / "sample.jsonl"
    sample.write_text('{"text":"a"}\n{"text":"b"}\n', encoding="utf-8")
    out = tmp_path / "out.parquet"

    config = {"schema": {"required_columns": ["text"], "column_types": {"text": "string"}}}
    convert_jsonl_to_parquet(str(sample), str(out), config, batch_size=1)
    pf = pq.ParquetFile(out)
    comp = pf.metadata.row_group(0).column(0).compression
    assert comp == "BROTLI"
    table = pf.read()
    assert table.num_rows == 2

    schema_path = out.with_name("schema.txt")
    assert schema_path.exists()
    expected = create_schema(config["schema"])
    lines = [l.strip() for l in schema_path.read_text().splitlines() if l.strip()]
    assert lines == [f"{f.name}:{f.type}" for f in expected]
