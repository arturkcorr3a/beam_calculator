from dataclasses import dataclass


@dataclass(frozen=True, kw_only=True)
class Clamps:
    """Store the U-shaped clamps that complete the anchorage at a beam extremity

    Attributes:
        diameter: Clamp bar diameter φ in mm.
        quantity: Number of clamps. Each clamp has two legs crossing the section.
        width: Clamp width in cm, equal to the stirrup width.
        length: Total clamp length l_c in cm.
    """

    diameter: float
    quantity: int
    width: float
    length: float
