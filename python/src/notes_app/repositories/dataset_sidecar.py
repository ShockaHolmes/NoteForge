"""Render and parse dataset sidecar YAML files.

Sidecar file naming convention: <data-filename>.dataset.yml
(e.g. sales-2026-q1.csv  →  sales-2026-q1.csv.dataset.yml)

For metadata-only datasets (no data file): <dataset-id>.dataset.yml
"""

import yaml

from notes_app.models.dataset import Dataset
from notes_app.models.dataset_metadata import DatasetMetadata


def render_sidecar(dataset: Dataset) -> str:
    """Serialise a Dataset to YAML for writing to a .dataset.yml sidecar."""
    return DatasetMetadata.from_dataset(dataset).to_yaml()


def parse_sidecar(text: str) -> Dataset:
    """Deserialise a .dataset.yml sidecar back into a Dataset domain object."""
    return DatasetMetadata.from_yaml(text).to_dataset()
