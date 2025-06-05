"""YunMin-EfficientData DEM (Data Efficiency Method) Module."""

from .train_individual import train_individual_domain
from .vector_diff import compute_vector_diff
from .merge_model import merge_models

__version__ = "1.0.0"
__all__ = [
    "train_individual_domain",
    "compute_vector_diff",
    "merge_models",
]
