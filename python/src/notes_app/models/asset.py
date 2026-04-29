"""Shared asset interface and type discriminator."""

from datetime import datetime
from enum import Enum
from typing import Protocol, runtime_checkable


class AssetType(Enum):
    """Discriminator that identifies whether an asset is a note or dataset."""

    NOTE = "note"
    DATASET = "dataset"


@runtime_checkable
class Asset(Protocol):
    """
    Structural interface satisfied by all asset types (notes, datasets).

    Any class that exposes these attributes and the ``asset_type`` property
    is considered an ``Asset`` — no explicit inheritance required, though
    subclassing is encouraged for clarity.
    """

    id: str
    title: str
    author: str
    created: datetime
    modified: datetime
    tags: tuple[str, ...]

    @property
    def asset_type(self) -> AssetType:
        """Returns the concrete type of this asset."""
        ...
