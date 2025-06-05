"""Placeholder tests for format module."""

from unittest.mock import MagicMock
import sys

sys.modules.setdefault("pandas", MagicMock())
sys.modules.setdefault("pyarrow", MagicMock())
sys.modules.setdefault("pyarrow.parquet", MagicMock())

from format.to_parquet import main as to_parquet_main  # type: ignore


def test_to_parquet_exists() -> None:
    """Ensure conversion entrypoint exists."""
    assert callable(to_parquet_main)
