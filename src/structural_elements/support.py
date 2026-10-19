from dataclasses import dataclass


@dataclass(frozen=True)
class Support:
    """A beam support's extent along the beam axis

    Attributes:
        center: Theoretical support position, where the analysis model places
            it (cm).
        left: Left face position (cm).
        right: Right face position (cm).
    """

    center: float
    left: float
    right: float

    def __post_init__(self) -> None:
        """Validate that the center lies between the faces

        Raises:
            ValueError: If the faces are not ordered as left <= center <= right.
        """
        if not self.left <= self.center <= self.right:
            raise ValueError(
                "Support faces must satisfy left <= center <= right. "
                f"Got left={self.left}, center={self.center}, right={self.right} cm."
            )
