from dataclasses import dataclass

@dataclass
class Pillar:
    """
    Represents a structural pillar, acting as a node in the pavement grid.

    Attributes:
        id: Unique identifier (e.g. "P1")
        x: Physical x-coordinate (cm)
        y: Physical y-coordinate (cm)
        width: Cross-section width (cm)
        depth: Cross-section depth (cm)
    """
    id: str
    x: float
    y: float
    width: float
    depth: float
