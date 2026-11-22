"""Dataclass models for ABNT NBR 6120:2019 - Section 5.4 - Table 7 (Fills)."""

from dataclasses import dataclass

from src.errors import TableLookupError
from src.logger import log_property, logger_label


@dataclass(frozen=True)
class FillMaterial:
    """A fill material with its apparent specific weight."""

    description: str
    weight_min: float | None
    weight_max: float | None
    weight_avg: float


@logger_label("ABNT NBR 6120:2019 - Table 7")
@dataclass(frozen=True)
class Table7:
    """ABNT NBR 6120:2019 - Section 5.4 - Table 7 (Fills).

    Attributes:
        title: Table title.
        reference: Normative reference.
        description: Human-readable description of the table contents.
        units: Mapping of physical quantity to unit string.
        materials: Fill materials.
    """

    title: str
    reference: str
    description: str
    units: dict[str, str]
    materials: tuple[FillMaterial, ...]

    def find_material(self, description: str) -> FillMaterial:
        """Find a material by (partial, case-insensitive) description match."""
        query = description.lower()
        for material in self.materials:
            if query in material.description.lower():
                log_property(
                    f"fill material: '{material.description}', avg={material.weight_avg} kN/m³"
                )
                return material
        raise TableLookupError(
            f"No material matching '{description}' was found.",
            table="ABNT NBR 6120:2019 — Table 7",
            value=description,
        )
