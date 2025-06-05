"""Placeholder tests for DEM module."""

from dem.train_individual import train_individual_domain
from dem.vector_diff import compute_vector_diff
from dem.merge_model import merge_models


def test_dem_functions_exist() -> None:
    """Check that DEM functions are callable."""
    assert callable(train_individual_domain)
    assert callable(compute_vector_diff)
    assert callable(merge_models)
