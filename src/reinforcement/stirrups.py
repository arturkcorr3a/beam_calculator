from dataclasses import dataclass
from functools import cached_property
from itertools import pairwise
from math import pi
from typing import cast

from src.analysis.beam_analysis import BeamAnalysis
from src.calculators.stirrup_calculator import (
    MIN_SPACING,
    REDUCED_SPACING_SHEAR_RATIO,
    StirrupCalculator,
)
from src.loading.forces import LOAD_FACTOR, design_effort_elu
from src.logger import log_element, log_operation, log_property, logger_label
from src.properties.steel import Steel
from src.structural_elements.rectangular_beam import RectangularBeam

MIN_DIAMETER = 0.5  # cm, minimum diameter of stirrup bars (NBR 6118 - Section 18.3.3.2)
HOOK_TIP_RATIO = 5  # 135° hook tip, in bar diameters (NBR 6118 - Section 9.4.6.1)
MIN_HOOK_TIP = 5.0  # cm, shortest 135° hook tip (NBR 6118 - Section 9.4.6.1)


@dataclass(frozen=True, slots=True)
class StirrupZone:
    """Stretch of a span with a constant stirrup spacing

    Attributes:
        start: Zone start along the beam (cm).
        end: Zone end along the beam (cm).
        spacing: Stirrup spacing in the zone (cm).
    """

    start: float
    end: float
    spacing: float


@logger_label("Stirrups - {id}")
class Stirrups:
    """Class to manage stirrup reinforcement properties."""

    def __init__(
        self, beam: RectangularBeam, calculator: StirrupCalculator, id: str = ""
    ):
        """
        Initialize Stirrups.
        """
        self.beam = beam
        self.steel = beam.steel  # Access steel properties from the beam
        self.calculator = calculator  # Access stirrup calculation methods
        self.spacing: float | None = None  # cm, edge spacing (for the greatest shear)
        self.required_ratio: float | None = None
        self.diameter: float | None = None
        self.middle_spacing: float | None = None  # cm
        self.threshold_shear_force: float | None = (
            None  # kN, design shear resisted at the middle spacing
        )
        self.zones: list[StirrupZone] = []
        self.id = id

    @cached_property
    def max_diameter(self) -> float:
        """
        Calculate the maximum diameter of stirrup bars (phi_max) in cm, based on ABNT NBR 6118 - Section 18.3.3.2.
        """
        max_diameter = self.beam.width / 10  # cm
        log_property(f"Maximum stirrup diameter phi_max = {max_diameter:.2f} cm")
        return max_diameter

    def calculate_and_choose(self, effective_depth: float) -> tuple[float, float]:
        """
        Calculate the required stirrup reinforcement ratio and choose the appropriate diameter and spacing of stirrup bars.
        """
        self.calculator.calculate(effective_depth)
        self.required_ratio = self.calculator.required_ratio  # cm²/cm
        result = self.choose()  # Returns (spacing, diameter) in cm
        log_element(
            f"Stirrup: {cast(float, self.diameter) * 10:.0f}mm every {self.spacing:.1f} cm"
        )
        return result

    def choose(self) -> tuple[float, float]:
        """
        Choose the diameter and spacing of stirrup bars based on the required reinforcement ratio, minimum spacing, and maximum diameter.

        Raises:
            ValueError: If no diameter and spacing combination meets the
                required ratio (infeasible shear design).
        """
        options: list[tuple[float, float]] = []

        spacing = self.calculator.max_spacing

        while spacing > MIN_SPACING:
            diameter = self.pick_diameter_for_spacing(spacing)
            if diameter is not None:
                options.append((spacing, diameter))
            spacing -= 1

        if not options:
            raise ValueError(
                f"No stirrup meets A_sw/s = {cast(float, self.required_ratio):.4f} cm²/cm "
                f"with diameters from {MIN_DIAMETER * 10:.1f} to {self.max_diameter * 10:.1f} mm "
                f"and spacings above {MIN_SPACING:.1f} cm up to s_max = {self.calculator.max_spacing:.1f} cm."
            )

        best_option = self._pick_best_option(options)
        self.spacing, self.diameter = best_option
        return best_option

    @staticmethod
    def _pick_best_option(options: list[tuple[float, float]]) -> tuple[float, float]:
        """
        Choose the option with the best ratio
        """
        option_ratios = [
            (spacing, diameter, Stirrups.calculate_ratio(diameter, spacing))
            for spacing, diameter in options
        ]
        option_ratios.sort(
            key=lambda x: x[2], reverse=False
        )  # Sort by ratio, ascending
        return option_ratios[0][:2]  # Return spacing and diameter of the best option

    def pick_diameter_for_spacing(self, spacing: float) -> float | None:
        """
        Pick the diameter (cm) of stirrup bars for a given spacing to meet the required reinforcement ratio.
        """
        for diameter in self.steel.available_sizes:
            diameter = diameter / 10  # cm; Ensure diameter is at least the minimum
            if not MIN_DIAMETER <= diameter <= self.max_diameter:
                continue  # skips invalid diameters
            ratio = Stirrups.calculate_ratio(diameter, spacing)
            if ratio >= cast(float, self.required_ratio):
                return diameter
        return None

    def distribute(
        self, analysis: BeamAnalysis, start: float, end: float
    ) -> list[StirrupZone]:
        """Split a span into stirrup zones: the chosen spacing where the shear is high, the middle spacing elsewhere.

        The chosen diameter is kept. The middle spacing is used wherever the design shear |V_Sd| does not exceed the threshold shear force it resists; the chosen (edge) spacing is used elsewhere. Must run after ``calculate_and_choose``.

        Args:
            analysis: Structural analysis of the beam (characteristic forces).
            start: Span start along the beam (cm).
            end: Span end along the beam (cm).

        Returns:
            Zones covering [start, end], left to right; neighboring zones have different spacings.
        """
        edge_spacing = cast(float, self.spacing)  # cm
        self.middle_spacing = max(self._middle_spacing(), edge_spacing)  # cm
        if self.middle_spacing == edge_spacing:
            self.threshold_shear_force = None
            self.zones = [StirrupZone(start, end, edge_spacing)]
            log_operation(
                f"Chosen spacing is already the largest allowed; no scaling ({edge_spacing:.1f} cm)"
            )
            return self.zones

        self.threshold_shear_force = self._threshold_shear_force()  # kN
        self.zones = self._zones(analysis, start, end)
        zones_description = " | ".join(
            f"c/{zone.spacing:.1f} [{zone.start:.1f}–{zone.end:.1f}]"
            for zone in self.zones
        )
        log_element(f"Stirrup zones: {zones_description} cm")
        return self.zones

    def _middle_spacing(self) -> float:
        """Return the largest spacing (cm) of the chosen diameter that meets the minimum ratio within the low-shear s_max.

        Steps down 1 cm from s_max like ``choose``; falls back to the chosen spacing if no step meets the minimum ratio.
        """
        diameter = cast(float, self.diameter)  # cm
        minimum_ratio = self.calculator.minimum_ratio  # cm²/cm
        spacing = self.calculator.max_spacing_for(
            0.0
        )  # cm, any shear below the reduced-spacing limit gives the low-shear s_max
        while spacing > MIN_SPACING:
            if Stirrups.calculate_ratio(diameter, spacing) >= minimum_ratio:
                log_operation(f"Middle stirrup spacing = {spacing:.1f} cm")
                return spacing
            spacing -= 1
        return cast(float, self.spacing)

    def _threshold_shear_force(self) -> float:
        """Return the design shear force (kN) resisted by the chosen diameter at the middle spacing.

        Capped at REDUCED_SPACING_SHEAR_RATIO V_Rd2, above which the middle spacing would exceed s_max (NBR 6118 - Section 18.3.3.2).
        """
        ratio = Stirrups.calculate_ratio(
            cast(float, self.diameter), cast(float, self.middle_spacing)
        )  # cm²/cm
        shear_resistance = self.calculator.shear_resistance(ratio)  # kN
        reduced_spacing_limit = (
            REDUCED_SPACING_SHEAR_RATIO * self.calculator.compressed_strut_resistance
        )  # kN
        threshold_shear_force = min(shear_resistance, reduced_spacing_limit)
        log_operation(f"Threshold shear force V_lim = {threshold_shear_force:.2f} kN")
        return threshold_shear_force

    def _zones(
        self, analysis: BeamAnalysis, start: float, end: float
    ) -> list[StirrupZone]:
        """Split [start, end] (cm) where |V_Sd| crosses the threshold shear force, merging neighbors with the same spacing."""
        threshold = cast(float, self.threshold_shear_force)  # kN, design
        characteristic_threshold = threshold / LOAD_FACTOR  # kN
        crossings = analysis.positions_for_shear(
            characteristic_threshold
        ) + analysis.positions_for_shear(-characteristic_threshold)  # cm
        bounds = [start, *sorted(x for x in crossings if start < x < end), end]

        zones: list[StirrupZone] = []
        for zone_start, zone_end in pairwise(bounds):
            middle = (zone_start + zone_end) / 2  # cm
            design_shear_force = design_effort_elu(abs(analysis.shear_force(middle)))
            spacing = (
                cast(float, self.spacing)
                if design_shear_force > threshold
                else cast(float, self.middle_spacing)
            )  # cm
            if zones and zones[-1].spacing == spacing:
                zones[-1] = StirrupZone(zones[-1].start, zone_end, spacing)
            else:
                zones.append(StirrupZone(zone_start, zone_end, spacing))
        return zones

    @staticmethod
    def closed_length_for(
        width: float, height: float, diameter_mm: float, steel: Steel
    ) -> float:
        """Return the cut length of a closed two-leg stirrup with 135° hooks (cm)

        Measured along the bar's axis: the four straight sides, three 90° corners, and the closing corner, where each end bends 135° and carries a straight tip.

        Args:
            width: Outer width of the stirrup (cm).
            height: Outer height of the stirrup (cm).
            diameter_mm: Stirrup bar diameter φ_t (mm).
            steel: Steel of the bar, for the bend diameter.

        Raises:
            ValueError: Propagated from the bend diameter if the norm gives none for the bar.

        References:
            ABNT NBR 6118:2026 — Section 9.4.6.1, Table 9.2
        """
        diameter = diameter_mm / 10  # cm
        bend_diameter = steel.stirrup_bend_diameter(diameter_mm)  # cm
        axis_radius = (bend_diameter + diameter) / 2  # cm
        sides = 2 * (width + height) - 8 * (bend_diameter / 2 + diameter)  # cm
        corners = 3 * (pi / 2) * axis_radius  # cm
        hook_arcs = 2 * (3 * pi / 4) * axis_radius  # cm
        tips = 2 * max(HOOK_TIP_RATIO * diameter, MIN_HOOK_TIP)  # cm
        return sides + corners + hook_arcs + tips

    @staticmethod
    def calculate_ratio(diameter: float, spacing: float) -> float:
        """
        Calculate the reinforcement ratio (A_sw/s) for a given diameter (cm) and spacing (cm) of stirrup bars.
        """
        area = pi * (diameter / 2) ** 2  # cm²
        return 2 * area / spacing  # cm²/cm, factor 2 for two legs of the stirrup
