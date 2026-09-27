from typing import cast

from indeterminatebeam import Beam, Support  # type: ignore
from indeterminatebeam.loading import UDLV  # type: ignore
from sympy import Expr  # type: ignore

from src.config import APP_CONFIG
from src.logger import log_element, logger_label
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
class RectangularBeam(Beam, metaclass=_BeamMeta):
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
        loads: list[UDLV],
        label: str = "",
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
        self.label = label
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

        log_element(
            f"{self.width:.0f} x {self.height:.0f} cm; {self.length / 100.0:.2f} m long, {self.concrete.name}, {self.steel.name}"
        )

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

    @property
    def area(self) -> float:
        """
        Returns the cross-sectional area (cm²) of the beam.
        """
        return self._A

    @property
    def bending_moment_expression(self) -> Expr:
        """Return the symbolic bending moment M(x) expression in x (kN.m; x in cm)."""
        return self._bending_moments  # type: ignore[return-value]

    @property
    def shear_force_expression(self) -> Expr:
        """Return the symbolic shear force V(x) expression in x (kN; x in cm)."""
        return self._shear_forces  # type: ignore[return-value]

    def get_max_bending_moment(self) -> tuple[float, float]:
        """
        Returns a tuple (max_bending_moment, position) for the largest-magnitude
        bending moment (kN.m) along the beam and the x-coordinate (cm) where it occurs.

        Exact, since with UDLV-only loading, shear force is piecewise-linear
        everywhere: critical points can only occur at supports or UDL span
        edges, or at interior shear zero-crossings (found here by exact linear
        interpolation between those breakpoints).
        """
        breakpoints: set[float] = {0.0, float(self._x1)}
        breakpoints.update(float(support._position) for support in self._supports)  # type: ignore
        for load in self._loads:  # type: ignore
            x0, x1 = cast(tuple[float, float], load.span)  # type: ignore
            breakpoints.add(float(x0))
            breakpoints.add(float(x1))

        sorted_breakpoints: list[float] = sorted(breakpoints)

        raw_shear = self.get_shear_force(*sorted_breakpoints)  # type: ignore
        shear_values: list[float] = [float(v) for v in cast(list[float], raw_shear)]

        candidates: set[float] = set(sorted_breakpoints)
        for i in range(len(sorted_breakpoints) - 1):
            x0, x1 = sorted_breakpoints[i], sorted_breakpoints[i + 1]
            v0, v1 = shear_values[i], shear_values[i + 1]
            if v0 * v1 < 0:
                x_zero: float = x0 - v0 * (x1 - x0) / (v1 - v0)
                candidates.add(x_zero)

        sorted_candidates: list[float] = sorted(candidates)
        raw_moments = self.get_bending_moment(*sorted_candidates)  # type: ignore
        moment_values: list[float] = [float(m) for m in cast(list[float], raw_moments)]

        idx: int = max(range(len(moment_values)), key=lambda i: abs(moment_values[i]))
        return moment_values[idx], sorted_candidates[idx]
