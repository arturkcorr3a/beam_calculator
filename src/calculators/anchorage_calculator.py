from typing import cast

from src.calculators.stirrup_calculator import StirrupCalculator
from src.logger import log_property, logger_label
from src.properties.concrete import Concrete
from src.properties.steel import Steel
from src.reinforcement.reinforcement import Reinforcement


@logger_label("Anchorage Calculator")
class AnchorageCalculator:
    def __init__(
        self,
        *,  # This forces the use of keyword arguments for clarity
        stirrup_calculator: StirrupCalculator,
        steel: Steel,
        concrete: Concrete,
        layer_index: int,
        reinforcement: Reinforcement,
    ):
        self.stirrup_calculator = stirrup_calculator
        self.steel = steel
        self.concrete = concrete
        self.layer = reinforcement.chosen_bars[layer_index]
        self.reinforcement = reinforcement
        self.beam_height = self.reinforcement.beam.height  # cm

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

        adherence_zone = "good" if layer_has_good_adherence else "poor"
        log_property(f"Adherence Zone: {adherence_zone}")
        log_property(f"Adherence Coefficient (eta_2) = {eta_2:.4f}")
        return eta_2

    @property
    def max_diameter(self) -> float:
        """Get the maximum bar diameter (mm) in the layer."""
        return max(bar.diameter_mm for bar in self.layer.bars)

    @property
    def diameter_coefficient(self) -> float:
        """Calculate the adherence coefficient (eta_3) for maximum bar diameter in the layer, based on ABNT NBR 6118 - Section 9.3.1"""
        eta_3 = min((132 - self.max_diameter) / 100, 1.00)
        log_property(f"Diameter Coefficient (eta_3) = {eta_3:.4f}")
        return eta_3

    @property
    def basic_anchorage_length(self) -> float:
        """Calculate the basic anchorage length (l_b) in cm, based on NBR 6118 - Section 9.4.2.4"""
        max_diameter_cm = self.max_diameter / 10  # Convert mm to cm
        l_b = (max_diameter_cm / 4) * (self.steel.fyd / self.design_bond_strength)
        l_b = max(25 * max_diameter_cm, l_b)
        log_property(f"Basic Anchorage Length (l_b) = {l_b:.2f} cm")
        return l_b

    @property
    def anchorage_alpha_coefficient(self) -> float:
        """Calculate the anchorage alpha coefficient (alpha) based on NBR 6118 - Section 9.4.2.5"""
        has_hook = any(bar.has_hook for bar in self.layer.bars)
        alpha = 0.7 if has_hook else 1.0
        log_property(f"Anchorage Alpha Coefficient (alpha) = {alpha:.4f}")
        return alpha

    @property
    def necessary_anchorage_length(self) -> float:
        """Calculate the necessary anchorage length (l_b,nec) in cm, based on NBR 6118 - Section 9.4.2.5"""
        l_b_nec = (
            self.anchorage_alpha_coefficient
            * self.basic_anchorage_length
            * (cast(float, self.reinforcement.required_area) / self.reinforcement.area)
        )
        l_b_nec = max(l_b_nec, self.min_anchorage_length)
        log_property(f"Necessary Anchorage Length (l_b,nec) = {l_b_nec:.2f} cm")
        return l_b_nec

    @property
    def min_anchorage_length(self) -> float:
        """Calculate the minimum anchorage length (l_b,min) in cm, based on NBR 6118 - Section 9.4.2.5"""
        l_b_min = max(
            0.3 * self.basic_anchorage_length, 10 * (self.max_diameter / 10), 10
        )
        log_property(f"Minimum Anchorage Length (l_b,min) = {l_b_min:.2f} cm")
        return l_b_min

    # TODO actually use this function when dimensioning the rebars
    # TODO analyse available x required and act accordingly
    # TODO scale the layers
    # TODO analisar armadura transversal na ancoragem (9.4.2.6)