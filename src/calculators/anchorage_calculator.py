# Calculations of necessary anchorage length

# Input: whatever is necessary

# Output: length in cm

from src.calculators.stirrup_calculator import StirrupCalculator
from src.logger import log_property, logger_label
from src.properties.concrete import Concrete
from src.properties.steel import Steel
from src.structural_elements.rebar import Rebar


@logger_label("Anchorage Calculator")
class AnchorageCalculator:
    def __init__(
        self,
        stirrup_calculator: StirrupCalculator,
        steel: Steel,
        concrete: Concrete,
        layer: list[Rebar],
    ):
        self.stirrup_calculator = stirrup_calculator
        self.steel = steel
        self.concrete = concrete
        self.layer = layer

    @property
    def _moment_shift_length(self):
        return self.stirrup_calculator.calculate_moment_shift()

    def design_bond_strength(self) -> float:
        """Calculate the design bond strength (f_bd) in kN/cm. NBR 6118 - Section 9.3.2.1"""
        eta_1 = self.steel.bond_coefficient
        eta_2 = self.adherence_coefficient
        eta_3 = self.diameter_coefficient
        f_bd = eta_1 * eta_2 * eta_3 * self.concrete.fctd
        log_property(f"Design Bond Strength (f_bd) = {f_bd:.4f} kN/cm")
        return f_bd

    @property
    def adherence_coefficient(self) -> float:
        """Calculate the adherence coefficient (eta_2) for the given steel type, based on ABNT NBR 6118 - Section 9.3.1"""
        is_layer_with_good_adherence = True  #  TODO make this logic
        eta_2 = 1.0 if is_layer_with_good_adherence else 0.7
        log_property(f"Adherence Coefficient (eta_2) = {eta_2:.4f}")
        return eta_2

    @property
    def diameter_coefficient(self) -> float:
        """Calculate the adherence coefficient (eta_3) for the given steel type, based on ABNT NBR 6118 - Section 9.3.1"""
        eta_3 = min((132 - self.layer[0].diameter_mm) / 100, 1.00)
        log_property(f"Diameter Coefficient (eta_3) = {eta_3:.4f}")
        return eta_3
