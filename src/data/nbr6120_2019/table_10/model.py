"""Dataclass models for ABNT NBR 6120:2019 - Section 6.2 - Table 10 (Variable loads)."""

from dataclasses import dataclass

from src.logger import log_property, logger_label


@dataclass(frozen=True)
class LocationLoad:
    """A specific location within a category and its distributed variable load."""

    description: str
    distributed_load: float
    notes: tuple[str, ...]


@logger_label("ABNT NBR 6120:2019 - Table 10")
@dataclass(frozen=True)
class BuildingCategory:
    """A category of building or usage with its associated locations and loads."""

    description: str
    locations: tuple[LocationLoad, ...]

    def get_location_load(self, description: str) -> float:
        """Get the load for a specific location by (partial, case-insensitive) description match."""
        query = description.lower()
        for loc in self.locations:
            if query in loc.description.lower():
                log_property(f"live load for '{description}' = {loc.distributed_load:.2f} kN/m²")
                return loc.distributed_load
        raise KeyError(f"No location matching '{description}' was found.")


@logger_label("ABNT NBR 6120:2019 - Table 10")
@dataclass(frozen=True)
class Table10:
    """ABNT NBR 6120:2019 - Section 6.2 - Table 10 (Variable loads).

    Attributes:
        title: Table title.
        reference: Normative reference.
        description: Human-readable description of the table contents.
        units: Mapping of physical quantity to unit string.
        categories: Building categories mapped by an identifier string.
        footnotes: Footnotes mapped by their note letter.
    """

    title: str
    reference: str
    description: str
    units: dict[str, str]
    categories: tuple[BuildingCategory, ...]
    footnotes: dict[str, str]

    def find_category(self, description: str) -> BuildingCategory:
        """Find a building category by (partial, case-insensitive) description match."""
        query = description.lower()
        for cat in self.categories:
            if query in cat.description.lower():
                log_property(f"occupancy category: '{cat.description}'")
                return cat
        raise KeyError(f"No category matching '{description}' was found.")
