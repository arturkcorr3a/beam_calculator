"""Dataclass models for ABNT NBR 6120:2019 - Section 5.4 - Table 2 (Masonry)."""

import math
from dataclasses import dataclass

from src.errors import TableLookupError
from src.logger import log_property, logger_label

THICKNESS_TOLERANCE_CM = 1e-9  # cm — absorbs float drift from unit conversions


@logger_label("ABNT NBR 6120:2019 - Table 2")
@dataclass(frozen=True)
class Thickness:
    """Self-weight (kN/m²) for a given nominal wall thickness with its associated coating thickness per face."""

    nominal_cm: float
    zero_cm: float
    one_cm: float | None
    two_cm: float | None

    def get_weight(self, coating_cm: int) -> float:
        """Return the weight for *coating_cm* (0, 1, or 2 cm per face)."""
        mapping: dict[int, float | None] = {
            0: self.zero_cm,
            1: self.one_cm,
            2: self.two_cm,
        }
        if coating_cm not in mapping:
            raise TableLookupError(
                f"Coating thickness must be 0, 1, or 2 cm. Got: {coating_cm}",
                table="ABNT NBR 6120:2019 — Table 2",
                value=coating_cm,
            )
        weight = mapping[coating_cm]
        if weight is None:
            raise TableLookupError(
                f"Weight for coating thickness {coating_cm} cm is not defined for nominal thickness {self.nominal_cm} cm.",
                table="ABNT NBR 6120:2019 — Table 2",
                value=coating_cm,
            )
        log_property(f"masonry weight({coating_cm} cm coating) = {weight:.2f} kN/m²")
        return weight


@logger_label("ABNT NBR 6120:2019 - Table 2")
@dataclass(frozen=True)
class MasonryType:
    """A masonry type entry (e.g. hollow concrete block) with its thicknesses."""

    type_description: str
    thicknesses: tuple[Thickness, ...]

    def get_thickness(self, nominal_cm: float) -> Thickness:
        """Look up a thickness entry by its nominal value (cm)."""
        for thickness in self.thicknesses:
            if math.isclose(
                thickness.nominal_cm, nominal_cm, abs_tol=THICKNESS_TOLERANCE_CM
            ):
                log_property(
                    f"'{self.type_description}' @ {nominal_cm} cm nominal → found"
                )
                return thickness
        raise TableLookupError(
            f"Nominal thickness {nominal_cm} cm not found for '{self.type_description}'",
            table="ABNT NBR 6120:2019 — Table 2",
            value=nominal_cm,
        )


@logger_label("ABNT NBR 6120:2019 - Table 2")
@dataclass(frozen=True)
class Table2:
    """ABNT NBR 6120:2019 - Section 5.4 - Table 2 (Masonry).

    Attributes:
        title: Table title.
        reference: Normative reference.
        description: Human-readable description of the table contents.
        units: Mapping of physical quantity to unit string.
        masonry: Non-bearing (infill) masonry types; structural masonry is out of scope.
        weight_composition_notes: Footnotes on weight composition assumptions.
    """

    title: str
    reference: str
    description: str
    units: dict[str, str]
    masonry: tuple[MasonryType, ...]
    weight_composition_notes: tuple[str, ...]

    def find_masonry_type(self, description: str) -> MasonryType:
        """Find a masonry type by (partial, case-insensitive) description match."""
        query = description.lower()
        for masonry in self.masonry:
            if query in masonry.type_description.lower():
                log_property(f"masonry: '{masonry.type_description}'")
                return masonry
        raise TableLookupError(
            f"No masonry type matching '{description}' was found.",
            table="ABNT NBR 6120:2019 — Table 2",
            value=description,
        )
