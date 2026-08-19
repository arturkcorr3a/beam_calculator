from typing import Optional

from src.elements.rectangular_beam import RectangularBeam
from src.reinforcement.stirrup_calculator import MIN_SPACING, StirrupCalculator
from math import pi

MIN_DIAMETER = 0.5  # cm, minimum diameter of stirrup bars (NBR 6118 - Section 18..3.3.2)

class Stirrups:
    """Class to manage stirrup reinforcement properties."""
    def __init__(self, beam: RectangularBeam, calculator: StirrupCalculator):
        """
        Initialize Stirrups.
        """
        self.beam = beam
        self.spacing = None  # cm, to be calculated
        self.diameter = None  # cm, to be calculated
        self.steel = beam.steel  # Access steel properties from the beam
        self.calculator = calculator  # Access stirrup calculation methods
        self.required_ratio = None  # cm²/cm, to be calculated

    @property
    def max_diameter(self) -> float:
        """
        Calculate the maximum diameter of stirrup bars (phi_max) in cm, based on the required reinforcement ratio and minimum spacing.
        """
        return self.beam.width / 10 # cm
    
    def calculate_and_choose(self, effective_depth: float) -> tuple[float, float]:
        """
        Calculate the required stirrup reinforcement ratio and choose the appropriate diameter and spacing of stirrup bars.
        """
        self.calculator.calculate(effective_depth)
        self.required_ratio = self.calculator.required_ratio  # cm²/cm
        return self.choose()  # Returns (spacing, diameter) in cm
    
    def choose(self) -> tuple[float, float]:
        """
        Choose the diameter and spacing of stirrup bars based on the required reinforcement ratio, minimum spacing, and maximum diameter.
        """
        options = []

        spacing = self.calculator.max_spacing
        diameter = self.pick_diameter_for_spacing(spacing)
        if diameter is not None:
            options.append((spacing, diameter))

        while spacing > MIN_SPACING:
            spacing -= 1
            diameter = self.pick_diameter_for_spacing(spacing)
            if diameter is not None:
                options.append((spacing, diameter))

        best_option = Stirrups._pick_best_option(options)
        self.spacing, self.diameter = best_option
        return best_option

    @staticmethod
    def _pick_best_option(options):
        """
        Choose the option with the best ratio
        """
        option_ratios = [(spacing, diameter,Stirrups.calculate_ratio(diameter, spacing)) for spacing, diameter in options]
        option_ratios.sort(key=lambda x: x[2], reverse=True)  # Sort by ratio, descending
        return option_ratios[0][:2]  # Return spacing and diameter of the best option

    def pick_diameter_for_spacing(self, spacing: float) -> Optional[float]:
        """
        Pick the diameter (cm) of stirrup bars for a given spacing to meet the required reinforcement ratio.
        """
        for diameter in self.steel.available_sizes:
            diameter = max(diameter/10, MIN_DIAMETER)  # cm; Ensure diameter is at least the minimum
            if diameter > self.max_diameter:
                continue 
            ratio = Stirrups.calculate_ratio(diameter, spacing)
            if ratio >= self.required_ratio:
                return diameter
        return None
    
    @staticmethod
    def calculate_ratio(diameter: float, spacing: float) -> float:
        """
        Calculate the reinforcement ratio (A_sw/s) for a given diameter (cm) and spacing (cm) of stirrup bars.
        """
        area = pi * (diameter / 2)**2  # cm²
        return 2 * area / spacing  # cm²/cm, factor 2 for two legs of the stirrup
    
    def print_report(self) -> None:
        """
        Print a report of the chosen stirrup reinforcement, including the required ratio, chosen diameter, and spacing.
        """
        print("\n------------------------------------------------------------")
        print("STIRRUPS")
        print("------------------------------------------------------------")
        print(f"Required ratio: {self.required_ratio:.4f} cm²/cm")
        print(f"Chosen: Φ {self.diameter*10} c/ {self.spacing} cm")
        print(f"Actual ratio: {Stirrups.calculate_ratio(self.diameter, self.spacing):.4f} cm²/cm")