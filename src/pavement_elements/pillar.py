from dataclasses import dataclass, field
from itertools import count

MIN_DIMENSION_CM = 14.0  # cm — ABNT NBR 6118 §13.2.3
MIN_AREA_CM2 = 360.0  # cm² — ABNT NBR 6118 §13.2.3


@dataclass
class Pillar:
    """
    Represents a structural pillar, acting as a node in the pavement grid.

    Attributes:
        id: Automatically generated unique identifier (e.g. "P1")
        x: Physical x-coordinate (cm)
        y: Physical y-coordinate (cm)
        width: Cross-section width (cm)
        depth: Cross-section depth (cm)
    """

    x: float
    y: float
    width: float
    depth: float
    id: str = field(default="", init=False)

    _counter = count(1)  # Class-level counter for auto-generating IDs

    def __post_init__(self):
        self.id = f"P{next(self._counter)}"  # Auto-generate ID if not provided
        self._validate_dimensions()

    def get_x_range(self) -> tuple[float, float]:
        """Returns the x-coordinate range of the pillar based on its width."""
        half = self.width / 2
        return (self.x - half, self.x + half)

    def get_y_range(self) -> tuple[float, float]:
        """Returns the y-coordinate range of the pillar based on its depth."""
        half = self.depth / 2
        return (self.y - half, self.y + half)

    def _validate_dimensions(self) -> None:
        """Enforce ABNT NBR 6118 minimum pillar cross-section requirements.

        Raises:
            ValueError: If either dimension is below 14 cm, or if the gross
                cross-sectional area is below 360 cm².

        References:
            ABNT NBR 6118:2014 — Section 13.2.3
        """
        if self.width < MIN_DIMENSION_CM or self.depth < MIN_DIMENSION_CM:
            raise ValueError(
                f"Pillar dimensions must be at least {MIN_DIMENSION_CM} cm. "
                f"Got {self.width}×{self.depth} cm."
            )
        if self.width * self.depth < MIN_AREA_CM2:
            raise ValueError(
                f"Pillar gross area must be at least {MIN_AREA_CM2} cm². "
                f"Got {self.width * self.depth:.1f} cm²."
            )
