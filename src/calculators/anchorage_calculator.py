from src.calculators.stirrup_calculator import StirrupCalculator
from src.logger import log_property, logger_label
from src.properties.concrete import Concrete
from src.properties.steel import Steel
from src.reinforcement.reinforcement import Layer


@logger_label("Anchorage Calculator")
class AnchorageCalculator:
    def __init__(
        self,
        *,  # This forces the use of keyword arguments for clarity
        stirrup_calculator: StirrupCalculator,
        steel: Steel,
        concrete: Concrete,
        layer: Layer,
        beam_height: float,
    ):
        self.stirrup_calculator = stirrup_calculator
        self.steel = steel
        self.concrete = concrete
        self.layer = layer
        self.beam_height = beam_height

    @property
    def _moment_shift_length(self):
        return self.stirrup_calculator.calculate_moment_shift()

    @property
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
        layer_has_good_adherence = self.layer.has_good_adherence(self.beam_height)
        eta_2 = 1.0 if layer_has_good_adherence else 0.7
        log_property(f"Adherence Coefficient (eta_2) = {eta_2:.4f}")
        return eta_2

    @property
    def diameter_coefficient(self) -> float:
        """Calculate the adherence coefficient (eta_3) for maximum bar diameter in the layer, based on ABNT NBR 6118 - Section 9.3.1"""
        max_diameter = max(bar.diameter_mm for bar in self.layer.bars)
        eta_3 = min((132 - max_diameter) / 100, 1.00)
        log_property(f"Diameter Coefficient (eta_3) = {eta_3:.4f}")
        return eta_3
