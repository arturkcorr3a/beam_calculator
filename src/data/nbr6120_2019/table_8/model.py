"""Dataclass models for ABNT NBR 6120:2019 - Section 5.4 - Table 8 (Ceilings, ducts and sprinklers)."""

from dataclasses import dataclass

from src.errors import TableLookupError
from src.logger import log_property, logger_label


@dataclass(frozen=True)
class CeilingDuctSprinklerMaterial:
    """A ceiling, duct, or sprinkler material with its associated weight."""

    description: str
    weight: float


@logger_label("ABNT NBR 6120:2019 - Table 8")
@dataclass(frozen=True)
class Table8:
    """ABNT NBR 6120:2019 - Section 5.4 - Table 8 (Ceilings, ducts and sprinklers).

    Attributes:
        title: Table title.
        reference: Normative reference.
        description: Human-readable description of the table contents.
        units: Mapping of physical quantity to unit string.
        materials: Ceiling, duct, and sprinkler materials.
    """

    title: str
    reference: str
    description: str
    units: dict[str, str]
    materials: tuple[CeilingDuctSprinklerMaterial, ...]

    def find_material(self, description: str) -> CeilingDuctSprinklerMaterial:
        """Find a material by (partial, case-insensitive) description match."""
        query = description.lower()
        for material in self.materials:
            if query in material.description.lower():
                log_property(f"ceiling/duct material: '{material.description}', weight={material.weight} kN/m²")
                return material
        raise TableLookupError(
            f"No material matching '{description}' was found.",
            table="ABNT NBR 6120:2019 — Table 8",
            value=description,
        )
