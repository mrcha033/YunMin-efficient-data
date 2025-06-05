"""Data utilities for YunMin-EfficientData.

This module hosts validation helpers and convenience functions for working
with JSONL datasets. Running ``python -m utils.data_utils`` exposes a small
command line tool for validating JSONL files or creating simple file manifests.

Example
-------
Validate a dataset::

    python -m utils.data_utils validate data/sample.jsonl

Generate a manifest::

    python -m utils.data_utils manifest *.jsonl --output manifest.json
"""

import json
import logging
from typing import Any, Dict, List, Optional, Tuple
from pathlib import Path
import re


def validate_jsonl_format(file_content: str, max_lines_check: int = 100) -> Tuple[bool, Dict[str, Any]]:
    """
    Validate JSONL file format and content

    Args:
        file_content: Content of the JSONL file as string
        max_lines_check: Maximum number of lines to check for validation

    Returns:
        Tuple of (is_valid, validation_info)
    """
    logger = logging.getLogger(__name__)

    lines = file_content.strip().split('\n')
    total_lines = len(lines)
    check_lines = min(max_lines_check, total_lines)

    validation_info = {
        'total_lines': total_lines,
        'checked_lines': check_lines,
        'valid_lines': 0,
        'invalid_lines': 0,
        'empty_lines': 0,
        'validation_errors': [],
        'sample_documents': [],
        'schema_fields': set(),
        'is_korean_content': False
    }

    for i, line in enumerate(lines[:check_lines]):
        line = line.strip()

        if not line:
            validation_info['empty_lines'] += 1
            continue

        try:
            doc = json.loads(line)
            validation_info['valid_lines'] += 1

            # Collect schema fields
            validation_info['schema_fields'].update(doc.keys())

            # Collect samples
            if len(validation_info['sample_documents']) < 5:
                validation_info['sample_documents'].append(doc)

            # Check for Korean content
            text = doc.get('text', '')
            if text and contains_korean(text):
                validation_info['is_korean_content'] = True

        except json.JSONDecodeError as e:
            validation_info['invalid_lines'] += 1
            error_msg = f"Line {i+1}: {str(e)}"
            validation_info['validation_errors'].append(error_msg)

            if len(validation_info['validation_errors']) < 10:  # Limit error messages
                logger.warning(f"JSON decode error at line {i+1}: {e}")

    # Calculate validity
    invalid_rate = validation_info['invalid_lines'] / max(check_lines, 1)
    is_valid = invalid_rate < 0.01  # Less than 1% invalid lines

    validation_info['invalid_rate'] = invalid_rate
    validation_info['schema_fields'] = list(validation_info['schema_fields'])

    return is_valid, validation_info


def contains_korean(text: str) -> bool:
    """
    Check if text contains Korean characters

    Args:
        text: Text to check

    Returns:
        True if text contains Korean characters
    """
    korean_pattern = re.compile(r'[\uac00-\ud7af\u1100-\u11ff\u3130-\u318f]')
    return bool(korean_pattern.search(text))


def validate_json(data: Any, required_fields: list[str] | None = None) -> tuple[bool, str]:
    """Validate a single JSON object.

    Parameters
    ----------
    data : Any
        Parsed JSON data to validate.
    required_fields : list[str] | None, optional
        Fields that must be present and not empty.

    Returns
    -------
    tuple[bool, str]
        ``(True, "")`` if valid, otherwise ``(False, reason)``.
    """

    if not isinstance(data, dict):
        return False, "Not a JSON object"

    if required_fields:
        for field in required_fields:
            value = data.get(field)
            if value is None or value == "" or value == []:
                return False, f"Missing or empty field: {field}"

    return True, ""


def validate_document_schema(doc: Dict, required_fields: List[str]) -> Tuple[bool, List[str]]:
    """
    Validate document schema

    Args:
        doc: Document dictionary
        required_fields: List of required field names

    Returns:
        Tuple of (is_valid, missing_fields)
    """
    missing_fields = []

    for field in required_fields:
        if field not in doc:
            missing_fields.append(field)
        elif doc[field] is None or doc[field] == "":
            missing_fields.append(f"{field} (empty)")

    return len(missing_fields) == 0, missing_fields


def normalize_document(doc: Dict) -> Dict:
    """
    Normalize document fields

    Args:
        doc: Original document

    Returns:
        Normalized document
    """
    import unicodedata

    normalized = {}

    # Normalize text content
    if 'text' in doc and doc['text']:
        text = str(doc['text'])
        # Unicode normalization
        text = unicodedata.normalize('NFKC', text)
        # Remove excessive whitespace
        text = ' '.join(text.split())
        normalized['text'] = text

    # Copy other fields
    for key, value in doc.items():
        if key != 'text':
            if isinstance(value, str):
                # Basic string normalization
                normalized[key] = value.strip()
            else:
                normalized[key] = value

    return normalized


def estimate_file_size(num_documents: int, avg_doc_size: int = 500) -> Dict[str, float]:
    """
    Estimate file sizes for different formats

    Args:
        num_documents: Number of documents
        avg_doc_size: Average document size in characters

    Returns:
        Dictionary with size estimates in MB
    """
    # Rough estimates based on typical compression ratios
    jsonl_size = (num_documents * avg_doc_size * 1.2) / (1024 * 1024)  # UTF-8 overhead
    parquet_size = jsonl_size * 0.3  # Parquet compression

    return {
        'jsonl_mb': round(jsonl_size, 2),
        'parquet_mb': round(parquet_size, 2),
        'compression_ratio': round(jsonl_size / parquet_size, 2) if parquet_size > 0 else 0
    }


def get_file_info(file_path: str) -> Dict[str, Any]:
    """
    Get information about a local file

    Args:
        file_path: Path to the file

    Returns:
        File information dictionary
    """
    path = Path(file_path)

    if not path.exists():
        return {'exists': False}

    stat = path.stat()

    return {
        'exists': True,
        'size_bytes': stat.st_size,
        'size_mb': round(stat.st_size / (1024 * 1024), 2),
        'modified_time': stat.st_mtime,
        'extension': path.suffix,
        'name': path.name,
        'stem': path.stem
    }


def create_file_manifest(files: List[str], output_path: str = None) -> Dict[str, Any]:
    """
    Create a manifest of files with metadata

    Args:
        files: List of file paths
        output_path: Optional path to save manifest

    Returns:
        Manifest dictionary
    """
    manifest = {
        'total_files': len(files),
        'files': [],
        'total_size_mb': 0,
        'formats': {}
    }

    for file_path in files:
        file_info = get_file_info(file_path)

        if file_info['exists']:
            manifest['files'].append({
                'path': file_path,
                'size_mb': file_info['size_mb'],
                'extension': file_info['extension']
            })

            manifest['total_size_mb'] += file_info['size_mb']

            # Count by format
            ext = file_info['extension']
            manifest['formats'][ext] = manifest['formats'].get(ext, 0) + 1

    manifest['total_size_mb'] = round(manifest['total_size_mb'], 2)

    # Save manifest if requested
    if output_path:
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(manifest, f, indent=2, ensure_ascii=False)

    return manifest


def split_dataset_by_domain(documents: List[Dict], domain_field: str = 'domain') -> Dict[str, List[Dict]]:
    """
    Split dataset by domain

    Args:
        documents: List of documents
        domain_field: Field name containing domain information

    Returns:
        Dictionary mapping domain names to document lists
    """
    domain_splits = {}

    for doc in documents:
        domain = doc.get(domain_field, 'unknown')

        if domain not in domain_splits:
            domain_splits[domain] = []

        domain_splits[domain].append(doc)

    return domain_splits


def calculate_dataset_statistics(documents: List[Dict]) -> Dict[str, Any]:
    """
    Calculate comprehensive dataset statistics

    Args:
        documents: List of documents

    Returns:
        Statistics dictionary
    """
    if not documents:
        return {'error': 'Empty dataset'}

    stats = {
        'total_documents': len(documents),
        'fields': {},
        'text_stats': {},
        'domains': {},
        'languages': {},
        'sources': {}
    }

    # Collect field statistics
    all_fields = set()
    for doc in documents:
        all_fields.update(doc.keys())

    for field in all_fields:
        field_values = [doc.get(field) for doc in documents if field in doc]
        non_null_values = [v for v in field_values if v is not None and v != ""]

        stats['fields'][field] = {
            'coverage': len(non_null_values) / len(documents),
            'unique_values': len(set(str(v) for v in non_null_values)) if non_null_values else 0
        }

    # Text statistics
    texts = [doc.get('text', '') for doc in documents if doc.get('text')]
    if texts:
        text_lengths = [len(text) for text in texts]
        stats['text_stats'] = {
            'avg_length': sum(text_lengths) / len(text_lengths),
            'min_length': min(text_lengths),
            'max_length': max(text_lengths),
            'total_characters': sum(text_lengths)
        }

    # Domain distribution
    for doc in documents:
        domain = doc.get('domain', 'unknown')
        stats['domains'][domain] = stats['domains'].get(domain, 0) + 1

    # Language distribution
    for doc in documents:
        lang = doc.get('lang', 'unknown')
        stats['languages'][lang] = stats['languages'].get(lang, 0) + 1

    # Source distribution
    for doc in documents:
        source = doc.get('source', 'unknown')
        stats['sources'][source] = stats['sources'].get(source, 0) + 1

    return stats


def _cli_validate(path: str) -> int:
    """Validate a JSONL file from the command line."""
    with open(path, "r", encoding="utf-8") as fh:
        content = fh.read()
    valid, info = validate_jsonl_format(content)
    print(json.dumps(info, indent=2, ensure_ascii=False))
    return 0 if valid else 1


def _cli_manifest(files: List[str], output: Optional[str]) -> int:
    """Create a manifest from CLI arguments."""
    manifest = create_file_manifest(files, output)
    print(json.dumps(manifest, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":  # pragma: no cover - CLI entry point
    import argparse

    parser = argparse.ArgumentParser(description="Utility CLI for data files")
    subparsers = parser.add_subparsers(dest="cmd", required=True)

    v_parser = subparsers.add_parser(
        "validate", help="Validate a JSONL file"
    )
    v_parser.add_argument("input", help="Path to JSONL file")

    m_parser = subparsers.add_parser(
        "manifest", help="Create a simple file manifest"
    )
    m_parser.add_argument("files", nargs="+", help="Files to include")
    m_parser.add_argument("--output", help="Where to save the manifest")

    args = parser.parse_args()

    if args.cmd == "validate":
        raise SystemExit(_cli_validate(args.input))
    raise SystemExit(_cli_manifest(args.files, args.output))
