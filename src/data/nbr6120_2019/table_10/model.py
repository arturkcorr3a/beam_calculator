"""Dataclass models for ABNT NBR 6120:2019 - Section 5.4 - Table 10 (Variable loads)."""

from dataclasses import dataclass


@dataclass(frozen=True)
class LocationLoad:
    """A specific location within a category and its distributed variable load."""

    description: str
    distributed_load: float
    notes: tuple[str, ...]


@dataclass(frozen=True)
class BuildingCategory:
    """A category of building or usage with its associated locations and loads."""

    description: str
    locations: tuple[LocationLoad, ...]


@dataclass(frozen=True)
class Table10:
    """ABNT NBR 6120:2019 - Section 5.4 - Table 10 (Variable loads).

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
                return cat
        raise KeyError(f"No category matching '{description}' was found.")
