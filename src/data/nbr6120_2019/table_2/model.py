"""Dataclass models for ABNT NBR 6120:2019 - Section 5.4 - Table 2 (Masonry)."""

from dataclasses import dataclass
from typing import Optional, overload

@dataclass(frozen=True)
class Thickness:
    """Self-weight (kN/m²) for a givem nominal wall thickness with its associated coating thickness per face."""

    nominal_cm: float
    zero_cm: float
    one_cm: Optional[float]
    two_cm: Optional[float]

    def get_weight(self, coating_cm: int) -> Optional[float]:
        """Return the weight for *coating_cm* (0, 1, or 2 cm per face)."""
        mapping = {0: self.zero_cm, 1: self.one_cm, 2: self.two_cm}
        if coating_cm not in mapping:
            raise ValueError(
                f"Coating thickness must be 0, 1, or 2 cm. Got: {coating_cm}"
            )
        return mapping[coating_cm]


@dataclass(frozen=True)
class MasonryType:
    """A masonry type entry (e.g. hollow concrete block) with its thicknesses."""

    type_description: str
    thicknesses: tuple[Thickness, ...]

    def get_thickness(self, nominal_cm: float) -> Thickness:
        """Look up a thickness entry by its nominal value (cm)."""
        for thickness in self.thicknesses:
            if thickness.nominal_cm == nominal_cm:
                return thickness
        raise ValueError(f"Nominal thickness {nominal_cm} cm not found for '{self.type_description}'")


@dataclass(frozen=True)
class Table2:
    """ABNT NBR 6120:2019 - Section 5.4 - Table 2 (Masonry).

    Attributes:
        title: Table title.
        reference: Normative reference.
        description: Human-readable description of the table contents.
        units: Mapping of physical quantity to unit string.
        structural_masonry: Masonry types classified as structural.
        non_bearing_masonry: Masonry types classified as non-bearing (infill).
        weight_composition_notes: Footnotes on weight composition assumptions.
    """

    title: str
    reference: str
    description: str
    units: dict[str, str]
    structural_masonry: tuple[MasonryType, ...]
    non_bearing_masonry: tuple[MasonryType, ...]
    weight_composition_notes: tuple[str, ...]

    def find_masonry_type(self, description: str) -> MasonryType:
        """Find a masonry type by (partial, case-insensitive) description match."""
        query = description.lower()
        for masonry in (*self.structural_masonry, *self.non_bearing_masonry):
            if query in masonry.type_description.lower():
                return masonry
        raise KeyError(f"No masonry type matching '{description}' was found.")

    @overload
    def find_masonry_type(self, description: str, structural: bool) -> MasonryType:
        """Find a masonry type by (partial, case-insensitive) description match, with a structural filter flag."""
        masonries = self.structural_masonry if structural else self.non_bearing_masonry

        query = description.lower()
        for masonry in masonries:
            if query in masonry.type_description.lower():
                return masonry
        raise KeyError(f"No masonry type matching '{description}' was found.")
