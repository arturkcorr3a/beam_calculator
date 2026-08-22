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
    id: str = field(default=None)  

    _counter = count(1)  # Class-level counter for auto-generating IDs

    def __post_init__(self):
        if self.id is None:
            self.id = f"P{next(self._counter)}"  # Auto-generate ID if not provided
