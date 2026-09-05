from dataclasses import dataclass, field
from itertools import count


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

    def get_x_range(self) -> tuple[float, float]:
        """Returns the x-coordinate range of the pillar based on its width."""
        half = self.width / 2
        return (self.x - half, self.x + half)

    def get_y_range(self) -> tuple[float, float]:
        """Returns the y-coordinate range of the pillar based on its depth."""
        half = self.depth / 2
        return (self.y - half, self.y + half)
