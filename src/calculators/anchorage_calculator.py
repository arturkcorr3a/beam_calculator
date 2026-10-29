from typing import TYPE_CHECKING, cast

from src.calculators.anchorage_clamp_calculator import (
    AnchorageClampCalculator,
    AnchorageClampCalculatorLabel,
)
from src.config import APP_CONFIG
from src.logger import log_operation, log_property, logger_label
from src.properties.steel import Steel
from src.reinforcement.clamps import Clamps
from src.structural_elements.rectangular_beam import RectangularBeam
from src.structural_elements.support import Support

if TYPE_CHECKING:
    from src.reinforcement.reinforcement import Reinforcement  # noqa: TC004

END_ZERO_TOLERANCE = 1e-3  # cm, zero-moment points this close to a beam end are ignored


@logger_label("Anchorage Calculator - {logging_info}")
class AnchorageCalculator:
    def __init__(
        self,
        *,  # This forces the use of keyword arguments for clarity
        moment_shift: float,
        steel: Steel,
        layer_index: int,
        reinforcement: Reinforcement,
        id: str = "",
    ):
        self.moment_shift = moment_shift  # cm, a_l
        self.steel = steel
        self.layer = reinforcement.chosen_bars[layer_index]
        self.reinforcement = reinforcement
        self.beam_height = self.reinforcement.beam.height  # cm
        self.id = id

    def run(
        self, available_space: float, left: bool, allow_clamp: bool = False
    ) -> Clamps | None:
        """Check the available space and set the layer bars' anchorage lengths

        Tries straight bars first, then hooked bars. If both fail and clamps are allowed at an extremity support, the hooked bars take the whole
        available space and clamps carry the rest of the force.

        Args:
            available_space: Length from the section to the bar's end (cm).
            left: Whether to anchor towards the left; otherwise the right.
            allow_clamp: Whether clamps may complete the anchorage when the
                hooked bars do not fit.

        Returns:
            The clamps set on the layer, or None if the bars anchor without them.

        Raises:
            ValueError: If there isn't enough space even with hooks, and clamps
                are not allowed or not possible at that end.
        """
        self.left = left
        self.logging_info = f"{self.id} ({'Left' if self.left else 'Right'})"
        passed = self._run_current_state(available_space, with_hooks=False)
        if passed:
            return None

        log_operation("Not enough space for anchorage; Add hooks and re-trying...")
        hooked_available_space = self.get_adjusted_available_space_for_hooks(
            available_space
        )
        passed = self._run_current_state(hooked_available_space, with_hooks=True)
        if passed:
            return None

        error_message = f"Not enough space for anchorage - even with hooks. Available: {available_space:.2f} cm, Required: {self.total_anchorage_length:.2f} cm. Consider reducing bar diameter."
        if not (allow_clamp and self._is_at_extremity_support):
            log_operation(error_message)
            raise ValueError(error_message)

        clamp_available_length = self.clamp_available_length
        if clamp_available_length <= 0:
            error_message += " No length inside the support for clamps."
            log_operation(error_message)
            raise ValueError(error_message)

        log_operation("Not enough space for anchorage with hooks; Adding clamps...")
        self.layer.set_anchorage_length(hooked_available_space, self.left)
        clamps = self._build_clamp_calculator(clamp_available_length).run()
        self.layer.set_clamps(self.left, clamps)
        return clamps

    def _build_clamp_calculator(
        self, clamp_available_length: float
    ) -> AnchorageClampCalculator:
        """Build the clamp calculator for the current side, with hooks enabled

        Args:
            clamp_available_length: Length inside the extremity support (cm).

        Raises:
            ValueError: If the reinforcement's effective depth or design shear
                is not set.
        """
        effective_depth = self.reinforcement.effective_depth
        design_shear = self.reinforcement.design_shear
        if effective_depth is None or design_shear is None:
            raise ValueError(
                "Effective depth and design shear must be set before calculating clamps."
            )
        return AnchorageClampCalculator(
            moment_shift=self.moment_shift,
            effective_depth=effective_depth,
            design_shear=design_shear,
            label_info=AnchorageClampCalculatorLabel(
                beam_label=self.reinforcement.beam.label, is_left=self.left
            ),
            available_length=clamp_available_length,
            necessary_length=self.necessary_anchorage_length,
            design_bond_strength=self.design_bond_strength,
            stirrup_inner_width=self.reinforcement.stirrup_inner_width,
        )

    @property
    def _extremity_support(self) -> Support:
        """Return the support the bars end in on the current side"""
        supports = self.reinforcement.beam.supports
        return supports[0] if self.left else supports[-1]

    @property
    def _is_at_extremity_support(self) -> bool:
        """Whether the bars end in a support on either end of the beam"""
        return self._extremity_support.is_extremity(self.reinforcement.beam.length)

    @property
    def clamp_available_length(self) -> float:
        """Calculate the anchorage length inside the extremity support

        Measured from the support's inner face to its outer face minus the
        effective covering.

        Returns:
            Length in cm; zero or negative when the support has no room.
        """
        support = self._extremity_support
        effective_covering = self.reinforcement.effective_covering()  # cm
        length = (support.right - support.left) - effective_covering
        log_property(f"Available length inside the support = {length:.2f} cm")
        return length

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
        """Calculate the bar length past the section, NBR 6118 - Section 18.3.2.3.1

        The greatest between l_b,nec and the length past the zero-moment point,
        plus the moment shift a_l.

        Returns:
            Length in cm.
        """
        # PAPER get ref
        total = (
            max(self.necessary_anchorage_length, self.length_past_zero_moment)
            + self.moment_shift
        )
        log_property(
            f"Total Anchorage Length (max(l_b,nec, l_M=0 + 10φ) + a_l) = {total:.2f} cm"
        )
        return total

    @property
    def length_past_zero_moment(self) -> float:
        """Calculate the length from the section to 10φ past the nearest zero-moment point on the current side, NBR 6118 - Section 18.3.2.3.1

        Zero-moment points at the beam ends are ignored.

        Returns:
            Length in cm; zero when there is no zero-moment point inside the
            beam on the current side.
        """
        center = self.reinforcement.center_position  # cm
        beam_length = self.reinforcement.beam.length  # cm
        inner_zeros = [
            zero
            for zero in self.reinforcement.moment_zeros
            if END_ZERO_TOLERANCE < zero < beam_length - END_ZERO_TOLERANCE
        ]
        if self.left:
            distances = [center - zero for zero in inner_zeros if zero < center]
        else:
            distances = [zero - center for zero in inner_zeros if zero > center]
        if not distances:
            return 0.0

        length = min(distances) + 10 * (self.max_diameter / 10)
        log_property(f"Length to zero moment + 10φ = {length:.2f} cm")
        return length

    @property
    def design_bond_strength(self) -> float:
        """Calculate the design bond strength (f_bd) in kN/cm². NBR 6118 - Section 9.3.2.1"""
        eta_1 = self.steel.bond_coefficient
        eta_2 = self.adherence_coefficient
        eta_3 = self.diameter_coefficient
        f_bd = eta_1 * eta_2 * eta_3 * APP_CONFIG.pavement_concrete.fctd
        log_property(f"Design Bond Strength (f_bd) = {f_bd:.4f} kN/cm²")
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
