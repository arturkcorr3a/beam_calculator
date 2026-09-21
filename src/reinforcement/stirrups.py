from functools import cached_property
from math import pi
from typing import cast

from src.calculators.stirrup_calculator import MIN_SPACING, StirrupCalculator
from src.logger import log_element, log_property, logger_label
from src.structural_elements.rectangular_beam import RectangularBeam

MIN_DIAMETER = 0.5  # cm, minimum diameter of stirrup bars (NBR 6118 - Section 18.3.3.2)


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
        self.spacing: float | None = None
        self.required_ratio: float | None = None
        self.diameter: float | None = None
        self.id = id

    @cached_property
    def max_diameter(self) -> float:
        """
        Calculate the maximum diameter of stirrup bars (phi_max) in cm, based on the required reinforcement ratio and minimum spacing.
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
        """
        options: list[tuple[float, float]] = []

        spacing = self.calculator.max_spacing

        while spacing > MIN_SPACING:
            diameter = self.pick_diameter_for_spacing(spacing)
            if diameter is not None:
                options.append((spacing, diameter))
            spacing -= 1

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

    @staticmethod
    def calculate_ratio(diameter: float, spacing: float) -> float:
        """
        Calculate the reinforcement ratio (A_sw/s) for a given diameter (cm) and spacing (cm) of stirrup bars.
        """
        area = pi * (diameter / 2) ** 2  # cm²
        return 2 * area / spacing  # cm²/cm, factor 2 for two legs of the stirrup
