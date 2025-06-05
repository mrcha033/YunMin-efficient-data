"""
Parquet utility functions for schema creation and validation
"""

import logging
from typing import Dict

import pyarrow as pa
import pyarrow.parquet as pq


def create_schema(schema_config: Dict) -> pa.Schema:
    """
    Create PyArrow schema from configuration

    Args:
        schema_config: Schema configuration dictionary

    Returns:
        PyArrow schema
    """
    required_columns = schema_config.get('required_columns', [])
    column_types = schema_config.get('column_types', {})

    fields = []

    for column in required_columns:
        column_type = column_types.get(column, 'string')

        if column_type == 'string':
            pa_type = pa.string()
        elif column_type == 'list[string]':
            pa_type = pa.list_(pa.string())
        elif column_type == 'categorical':
            pa_type = pa.string()  # Store as string, can be converted to categorical later
        else:
            pa_type = pa.string()  # Default to string

        fields.append(pa.field(column, pa_type))

    return pa.schema(fields)


def validate_parquet_file(file_path: str) -> bool:
    """
    Validate Parquet file integrity

    Args:
        file_path: Path to Parquet file

    Returns:
        True if file is valid, False otherwise
    """
    logger = logging.getLogger(__name__)

    try:
        # Try to read the file
        table = pq.read_table(file_path)

        # Basic validation
        if len(table) == 0:
            logger.warning(f"Parquet file {file_path} is empty")
            return False

        if len(table.columns) == 0:
            logger.warning(f"Parquet file {file_path} has no columns")
            return False

        # Check if we can convert to pandas (tests compatibility)
        df = table.to_pandas()

        logger.info(f"Parquet file {file_path} is valid: {len(table)} rows, {len(table.columns)} columns")
        return True

    except Exception as e:
        logger.error(f"Parquet file validation failed for {file_path}: {e}")
        return False


def get_parquet_info(file_path: str) -> Dict:
    """
    Get information about Parquet file

    Args:
        file_path: Path to Parquet file

    Returns:
        Dictionary with file information
    """
    try:
        parquet_file = pq.ParquetFile(file_path)
        table = parquet_file.read()

        info = {
            'num_rows': len(table),
            'num_columns': len(table.columns),
            'column_names': table.column_names,
            'schema': str(table.schema),
            'file_size_bytes': parquet_file.metadata.serialized_size,
            'num_row_groups': parquet_file.num_row_groups,
        }

        # Column statistics
        for i, column in enumerate(table.columns):
            col_name = table.column_names[i]
            info[f'{col_name}_null_count'] = column.null_count
            info[f'{col_name}_type'] = str(column.type)

        return info

    except Exception as e:
        logging.error(f"Failed to get Parquet info for {file_path}: {e}")
        return {}


def optimize_parquet_for_reading(input_file: str, output_file: str, row_group_size: int = 100000):
    """
    Optimize Parquet file for reading performance

    Args:
        input_file: Input Parquet file path
        output_file: Output optimized Parquet file path
        row_group_size: Target row group size
    """
    logger = logging.getLogger(__name__)

    try:
        # Read the original file
        table = pq.read_table(input_file)

        # Write with optimized settings
        pq.write_table(
            table,
            output_file,
            compression='snappy',  # Good balance of compression and speed
            row_group_size=row_group_size,
            use_dictionary=True,  # Enable dictionary encoding
            write_statistics=True,  # Enable column statistics
        )

        logger.info(f"Optimized Parquet file saved to: {output_file}")

    except Exception as e:
        logger.error(f"Failed to optimize Parquet file: {e}")
        raise
