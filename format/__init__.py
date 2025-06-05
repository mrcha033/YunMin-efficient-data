"""
YunMin-EfficientData Format Conversion Module

This module provides Youmu-based JSONL to Parquet conversion functionality.
"""

from .parquet_utils import create_schema, validate_parquet_file, get_parquet_info

try:  # Optional heavy dependency
    from .to_parquet import main as run_conversion
except Exception:  # pragma: no cover - may fail if deps missing
    run_conversion = None

__version__ = "1.0.0"
__all__ = [
    "run_conversion",
    "create_schema",
    "validate_parquet_file", 
    "get_parquet_info"
] 
