from src.config import APP_CONFIG
from src.logger import log_element, logger_label
from src.properties.concrete import Concrete
from src.properties.section_properties_calculator import SectionPropertiesCalculator
from src.properties.steel import Steel

_MIN_BEAM_WIDTH_CM = 12.0  # cm — ABNT NBR 6118 §13.2.2


class _BeamMeta(type):
    @property
    def nominal_covering(self) -> float:
        """
        Returns the nominal covering (cm) for the beam with the configured exposure class, with 10 mm execution tolerance, based on ABNT NBR 6118 - Section 7.4.
        """
        exposure_class = APP_CONFIG.exposure_class
        fck = Concrete[APP_CONFIG.pavement_concrete].value

        discount_for_concrete_greater_than_minimum = (
            0.5 if APP_CONFIG.is_concrete_greater_than_minimum(fck) else 0.0
        )  # cm — ABNT NBR 6118 - Section 7.4.7.6

        match exposure_class:
            case 1:
                return 2.5 - discount_for_concrete_greater_than_minimum
            case 2:
                return 3.0 - discount_for_concrete_greater_than_minimum
            case 3:
                return 4.0 - discount_for_concrete_greater_than_minimum
            case 4:
                return 5.0 - discount_for_concrete_greater_than_minimum
            case _:
                raise ValueError(
                    f"Invalid exposure class: {exposure_class}. Must be between 1 and 4."
                )


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
        concrete: Concrete,
        steel: Steel,
        label: str = "",
    ):
        """Initialize a rectangular beam section.

        Args:
            length: Beam length (cm).
            width: Cross-section width (cm).
            height: Cross-section height (cm).
            concrete: Concrete class (e.g. Concrete.C25).
            steel: Steel grade (e.g. Steel.CA50).
        """
        self.label = label
        self.width = width
        self.height = height
        self._validate_width()
        self.length = length
        self.concrete = concrete
        self.steel = steel

        log_element(
            f"{self.width:.0f} x {self.height:.0f} cm; {self.length / 100.0:.2f} m long, {self.concrete.name}, {self.steel.name}"
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

    @property
    def area(self) -> float:
        """
        Returns the cross-sectional area (cm²) of the beam.
        """
        return SectionPropertiesCalculator.rectangular_cross_sectional_area(
            self.width, self.height
        )
