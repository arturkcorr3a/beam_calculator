from indeterminatebeam import Beam, Support  # type: ignore
from indeterminatebeam.loading import Load  # type: ignore

from src.config import APP_CONFIG
from src.properties.concrete import Concrete
from src.properties.section_properties_calculator import SectionPropertiesCalculator
from src.properties.steel import Steel

UNITS = {
    "length": "cm",
    "force": "kN",
    "moment": "kN.m",
    "distributed": "kN/m",
    "stiffness": "kN/m",
    "A": "cm2",
    "G": "MPa",
    "E": "MPa",
    "I": "cm4",
    "deflection": "m",
}

_MIN_BEAM_WIDTH_CM = 12.0  # cm — ABNT NBR 6118 §13.2.2


class RectangularBeam(Beam):
    """
    Extends indeterminatebeam.Beam to a rectangular cross-section beam, with necessary properties and methods for dimensioning analysis.
    """

    def __init__(
        self,
        length: float,
        width: float,
        height: float,
        concrete: Concrete,
        steel: Steel,
        supports: list[Support],
        loads: list[Load],
    ):
        """Initialize a rectangular beam, with the analysis done.

        Args:
            length: Beam length (m).
            width: Cross-section width (cm).
            height: Cross-section height (cm).
            concrete: Concrete class (e.g. Concrete.C25).
            steel: Steel grade (e.g. Steel.CA50).
            supports: List of indeterminatebeam.Support instances.
            loads: List of indeterminatebeam.Load instances.
        """
        self.width = width
        self.height = height
        self._validate_width()
        calculated_moment_of_inertia = SectionPropertiesCalculator.moment_of_inertia(
            width, height
        )
        area = SectionPropertiesCalculator.rectangular_cross_sectional_area(
            width, height
        )
        shear_modulus = concrete.g_c
        elastic_modulus = concrete.ecs

        super().__init__(
            length,
            shear_modulus,
            round(elastic_modulus),
            calculated_moment_of_inertia,
            area,
        )
        self.update_units_local()

        self.length = length
        self.concrete = concrete
        self.steel = steel

        self.add_loads(*loads)  # type: ignore
        self.add_supports(*supports)  # type: ignore

        self.analyse()

    def update_units_local(self) -> None:
        for key, unit in UNITS.items():
            super().update_units(key, unit)

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

    def get_bending_moments(self) -> list[float]:
        """
        Returns a list of bending moments (kN.m) along the beam length, at each cm.
        """
        return [self.get_bending_moment(x) for x in range(int(self.length) + 1)]  # type: ignore

    def get_shear_forces(self) -> list[float]:
        """
        Returns a list of shear forces (kN) along the beam length, at each cm.
        """
        return [self.get_shear_force(x) for x in range(int(self.length) + 1)]  # type: ignore

    @property
    def nominal_covering(self) -> float:
        """
        Returns the nominal covering (cm) for the beam with class 2 exposure, with 10 mm execution tolerance, based on ABNT NBR 6118 - Section 7.4.
        """
        return APP_CONFIG.nominal_covering

    @property
    def area(self) -> float:
        """
        Returns the cross-sectional area (cm²) of the beam.
        """
        return self._A
