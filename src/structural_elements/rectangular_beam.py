from itertools import pairwise
from typing import assert_never

from src.config import APP_CONFIG
from src.config_options import ExposureClass
from src.logger import log_element, logger_label
from src.properties.section_properties_calculator import SectionPropertiesCalculator
from src.properties.steel import Steel
from src.structural_elements.support import Support

_MIN_BEAM_WIDTH_CM = 12.0  # cm — ABNT NBR 6118 §13.2.2
_FACE_TOLERANCE = 1e-3  # cm


class _BeamMeta(type):
    @property
    def nominal_covering(self) -> float:
        """
        Returns the nominal covering (cm) for the beam with the configured exposure class, with 10 mm execution tolerance, based on ABNT NBR 6118 - Section 7.4. The table value gets the discount for concrete stronger than the minimum and is then raised, if needed, to the minimum cover allowed by the maximum aggregate size (ABNT NBR 6118 - Section 7.4.7.6).
        """
        exposure_class = APP_CONFIG.exposure_class
        fck = APP_CONFIG.pavement_concrete.value

        discount_for_concrete_greater_than_minimum = (
            0.5 if APP_CONFIG.is_concrete_greater_than_minimum(fck) else 0.0
        )  # cm — ABNT NBR 6118 - Section 7.4.7.6

        match exposure_class:
            case ExposureClass.WEAK:
                table_cover = 2.5
            case ExposureClass.MODERATE:
                table_cover = 3.0
            case ExposureClass.SEVERE:
                table_cover = 4.0
            case ExposureClass.VERY_SEVERE:
                table_cover = 5.0
            case _:
                assert_never(exposure_class)

        return max(
            table_cover - discount_for_concrete_greater_than_minimum,
            APP_CONFIG.minimum_nominal_cover_for_aggregate(),
        )  # cm — ABNT NBR 6118 - Table 7.2 and Section 7.4.7.6


@logger_label("Structural {label}")
class RectangularBeam(metaclass=_BeamMeta):
    """A rectangular cross-section beam: geometry and materials used for dimensioning.

    Holds no structural analysis; see ``src.analysis.solver.analyse_beam``.
    """

    def __init__(
        self,
        length: float,
        width: float,
        height: float,
        steel: Steel,
        label: str = "",
        supports: list[Support] | None = None,
    ):
        """Initialize a rectangular beam section.

        Args:
            length: Beam length (cm).
            width: Cross-section width (cm).
            height: Cross-section height (cm).
            steel: Steel grade (e.g. Steel.CA50).
            supports: Supports along the beam, ordered left to right. Defaults
                to zero-width supports at both ends (0 and ``length``).

        Raises:
            ValueError: If the supports are out of order or overlap.
        """
        self.label = label
        self.width = width
        self.height = height
        self._validate_width()
        self.length = length
        self.steel = steel
        self.supports = (
            supports
            if supports is not None
            else [Support(0.0, 0.0, 0.0), Support(length, length, length)]
        )
        self._validate_supports()

        log_element(
            f"{self.width:.0f} x {self.height:.0f} cm; {self.length / 100.0:.2f} m long, {APP_CONFIG.pavement_concrete.name}, {self.steel.name}"
        )

    def _validate_width(self) -> None:
        """Enforce ABNT NBR 6118 minimum beam width requirement.

        Raises:
            ValueError: If width is below 12 cm.

        References:
            ABNT NBR 6118:2014 — Section 13.2.2
        """
        if self.width < _MIN_BEAM_WIDTH_CM:
            raise ValueError(
                f"Beam width must be at least {_MIN_BEAM_WIDTH_CM} cm. "
                f"Got {self.width} cm."
            )

    def _validate_supports(self) -> None:
        """Enforce that supports are ordered left to right without overlapping

        Raises:
            ValueError: If a support's left face lies before the previous
                support's right face.
        """
        for previous, current in pairwise(self.supports):
            if current.left < previous.right:
                raise ValueError(
                    "Supports must be ordered left to right without overlapping. "
                    f"Support at {current.center} cm starts at {current.left} cm, "
                    f"before the previous one ends at {previous.right} cm."
                )

    def get_support_face(self, position: float, left: bool) -> float:
        """Return the nearest support face to the left or right of a position

        Every face (left and right) of every support is a candidate, so a
        position inside a support returns one of that support's own faces.
        A face exactly on the position (within 1e-3 cm) counts on both sides.

        Args:
            position: Position along the beam (cm).
            left: Whether to search to the left of the position; otherwise to
                the right.

        Returns:
            Position of the nearest face along the beam (cm).

        Raises:
            ValueError: If there is no support face on the requested side.
        """
        faces = [face for s in self.supports for face in (s.left, s.right)]
        if left:
            candidates = [f for f in faces if f <= position + _FACE_TOLERANCE]
            nearest = max(candidates, default=None)
        else:
            candidates = [f for f in faces if f >= position - _FACE_TOLERANCE]
            nearest = min(candidates, default=None)

        if nearest is None:
            side = "left" if left else "right"
            raise ValueError(
                f"No support face to the {side} of position {position} cm."
            )
        return nearest

    @property
    def area(self) -> float:
        """
        Returns the cross-sectional area (cm²) of the beam.
        """
        return SectionPropertiesCalculator.rectangular_cross_sectional_area(
            self.width, self.height
        )
