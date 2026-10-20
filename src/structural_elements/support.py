from dataclasses import dataclass

_EXTREMITY_TOLERANCE = 1e-3  # cm


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

    def is_extremity(self, beam_length: float) -> bool:
        """Return whether the support sits on either end of the beam

        Args:
            beam_length: Length of the beam the support belongs to (cm).

        Returns:
            True if the center is at 0 or at ``beam_length``, within 1e-3 cm.
        """
        return (
            abs(self.center) <= _EXTREMITY_TOLERANCE
            or abs(self.center - beam_length) <= _EXTREMITY_TOLERANCE
        )
