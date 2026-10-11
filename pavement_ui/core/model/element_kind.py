"""Kinds of pavement elements the user registers."""

from enum import Enum


class ElementKind(Enum):
    """Kind of a registered element; the value is its ID prefix"""

    PILLAR = "P"
    BEAM = "V"
    SLAB = "L"

    @property
    def prefix(self) -> str:
        """ID prefix of the kind (e.g. "P" for pillars)"""
        return self.value
