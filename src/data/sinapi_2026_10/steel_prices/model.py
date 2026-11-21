"""Dataclass models for the SINAPI rebar prices (insumos)."""

from dataclasses import dataclass
from math import isclose

from src.logger import log_property, logger_label
from src.properties.steel import Steel


@dataclass(frozen=True, kw_only=True)
class SteelPrice:
    """A SINAPI rebar item and its unit price

    Attributes:
        code: SINAPI insumo code.
        description: SINAPI description, verbatim.
        steel: Steel grade.
        diameters_mm: Bar diameters φ (mm) the item covers.
        cut_and_bent: Whether the bars come cut and bent (dobrado e cortado)
            rather than as straight rebar (vergalhão).
        price_per_kg: Unit price (R$/kg).
    """

    code: int
    description: str
    steel: Steel
    diameters_mm: tuple[float, ...]
    cut_and_bent: bool
    price_per_kg: float

    def covers(self, steel: Steel, diameter_mm: float) -> bool:
        """Return whether the item prices the given grade and diameter"""
        return self.steel is steel and any(
            isclose(diameter_mm, covered) for covered in self.diameters_mm
        )


@logger_label("SINAPI - Steel prices")
@dataclass(frozen=True)
class SteelPriceTable:
    """SINAPI rebar prices (insumos)

    Attributes:
        title: Table title.
        reference: Source reference.
        description: Human-readable description of the table contents.
        units: Mapping of physical quantity to unit string.
        items: Rebar items.
    """

    title: str
    reference: str
    description: str
    units: dict[str, str]
    items: tuple[SteelPrice, ...]

    def price_for(self, steel: Steel, diameter_mm: float) -> SteelPrice:
        """Return the item that prices a bar: cut and bent when SINAPI has one, else straight rebar

        Raises:
            ValueError: If no item covers the grade and diameter.
        """
        candidates = [item for item in self.items if item.covers(steel, diameter_mm)]
        if not candidates:
            raise ValueError(f"No SINAPI price for {steel.name} φ{diameter_mm:g} mm.")
        item = max(candidates, key=lambda candidate: candidate.cut_and_bent)
        log_property(
            f"φ{diameter_mm:g} {steel.name}: SINAPI {item.code}, R$ {item.price_per_kg:.2f}/kg"
        )
        return item
