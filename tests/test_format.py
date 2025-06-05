"""Placeholder tests for format module."""

import pytest

pytest.importorskip("pandas")
pytest.importorskip("pyarrow")

from format.to_parquet import main as to_parquet_main  # type: ignore


def test_to_parquet_exists() -> None:
    """Ensure conversion entrypoint exists."""
    assert callable(to_parquet_main)
