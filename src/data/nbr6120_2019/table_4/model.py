"""Dataclass models for ABNT NBR 6120:2019 - Section 5.4 - Table 4 (Floor coverings and waterproofing)."""

from dataclasses import dataclass


@dataclass(frozen=True)
class ThicknessWeight:
    """Self-weight (kN/m²) for a given thickness (cm)."""

    thickness_cm: float | None
    weight: float


@dataclass(frozen=True)
class CoveringMaterial:
    """A floor covering or waterproofing material with its associated weights."""

    description: str
    thicknesses: tuple[ThicknessWeight, ...]

    def get_weight(self, thickness_cm: float | None = None) -> float:
        """Return the weight for the given thickness in cm."""
        for tw in self.thicknesses:
            if tw.thickness_cm == thickness_cm:
                return tw.weight
        raise ValueError(f"Thickness {thickness_cm} cm not found for '{self.description}'")


@dataclass(frozen=True)
class Table4:
    """ABNT NBR 6120:2019 - Section 5.4 - Table 4 (Floor coverings and waterproofing).

    Attributes:
        title: Table title.
        reference: Normative reference.
        description: Human-readable description of the table contents.
        units: Mapping of physical quantity to unit string.
        materials: Floor covering and waterproofing materials.
        notes: Footnotes on calculation and usage.
    """

    title: str
    reference: str
    description: str
    units: dict[str, str]
    materials: tuple[CoveringMaterial, ...]
    notes: tuple[str, ...]

    def find_material(self, description: str) -> CoveringMaterial:
        """Find a material by (partial, case-insensitive) description match."""
        query = description.lower()
        for material in self.materials:
            if query in material.description.lower():
                return material
        raise KeyError(f"No material matching '{description}' was found.")
