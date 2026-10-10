from typing import TYPE_CHECKING, cast

from src.logger import log_operation, log_property, logger_label
from src.properties.concrete import Concrete
from src.properties.steel import Steel
from src.structural_elements.rectangular_beam import RectangularBeam

if TYPE_CHECKING:
    from src.reinforcement.reinforcement import Reinforcement  # noqa: TC004


@logger_label("Anchorage Calculator - {logging_info}")
class AnchorageCalculator:
    def __init__(
        self,
        *,  # This forces the use of keyword arguments for clarity
        moment_shift: float,
        steel: Steel,
        concrete: Concrete,
        layer_index: int,
        reinforcement: Reinforcement,
        id: str = "",
    ):
        self.moment_shift = moment_shift  # cm, a_l
        self.steel = steel
        self.concrete = concrete
        self.layer = reinforcement.chosen_bars[layer_index]
        self.reinforcement = reinforcement
        self.beam_height = self.reinforcement.beam.height  # cm
        self.id = id

    def run(self, available_space: float, left: bool) -> None:
        """
        Checks the available space and sets the layer bars's lengths.
        If there isn't enough space, try to add hooks and recalculate.

        Raises a ValueError if there isn't enough space even after adding hooks.
        """
        self.left = left
        self.logging_info = f"{self.id} ({'Left' if self.left else 'Right'})"
        passed = self._run_current_state(available_space, with_hooks=False)
        if passed:
            return

        log_operation("Not enough space for anchorage; Add hooks and re-trying...")
        passed = self._run_current_state(
            self.get_adjusted_available_space_for_hooks(available_space),
            with_hooks=True,
        )
        if not passed:
            error_message = f"Not enough space for anchorage - even with hooks. Available: {available_space:.2f} cm, Required: {self.total_anchorage_length:.2f} cm. Consider reducing bar diameter."
            log_operation(error_message)
            raise ValueError(error_message)

    def _run_current_state(self, available_space: float, with_hooks: bool) -> bool:
        """
        Checks the available space and sets the layer bars's lengths.
        Returns True if the available space is enough, False otherwise.
        """
        self.layer.set_hooks(self.left, with_hooks)
        total_length = self.total_anchorage_length

        hooks_state = "with hooks" if with_hooks else "without hooks"
        if available_space >= total_length:
            self.layer.set_anchorage_length(total_length, self.left)
            log_operation(
                f"Anchorage length of {total_length:.2f} cm set {hooks_state}."
            )
            return True
        return False

    @property
    def total_anchorage_length(self) -> float:
        """Calculate the bar length past the section, l_b,nec plus the moment shift a_l

        Returns:
            Length in cm.
        """
        # PAPER get ref
        total = self.necessary_anchorage_length + self.moment_shift
        log_property(f"Total Anchorage Length (l_b,nec + a_l) = {total:.2f} cm")
        return total

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

    def _check_bars_have_hooks(self) -> bool:
        """Check if any bar in the layer has a hook."""
        if self.left:
            return any(bar.left_hook_enabled for bar in self.layer.bars)
        else:
            return any(bar.right_hook_enabled for bar in self.layer.bars)

    @property
    def anchorage_alpha_coefficient(self) -> float:
        """Calculate the anchorage alpha coefficient (alpha) based on NBR 6118 - Section 9.4.2.5"""
        has_hook = self._check_bars_have_hooks()
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

    def get_adjusted_available_space_for_hooks(
        self, regular_available_space: float
    ) -> float:
        """
        Tensioned bars with hooks must have a minimum concrete cover of 3 times the bar diameter, per ABNT NBR 6118 - Section 9.4.2.5. This method calculates the adjusted available space for anchorage when hooks are present, ensuring that the minimum cover requirement is met.
        """
        beam_coverage = RectangularBeam.nominal_covering  # cm
        min_coverage_for_hooks = 3 * (self.max_diameter / 10)  # cm
        adjusted_coverage = max(beam_coverage, min_coverage_for_hooks)
        return regular_available_space + beam_coverage - adjusted_coverage
