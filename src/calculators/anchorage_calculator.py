from typing import TYPE_CHECKING, cast

from src.calculators.anchorage_clamp_calculator import (
    AnchorageClampCalculator,
    AnchorageClampCalculatorLabel,
)
from src.config import APP_CONFIG
from src.loading.forces import design_effort_elu
from src.logger import log_operation, log_property, logger_label
from src.properties.steel import Steel
from src.reinforcement.clamps import Clamps
from src.structural_elements.rectangular_beam import RectangularBeam
from src.structural_elements.support import Support

if TYPE_CHECKING:
    from src.reinforcement.reinforcement import Reinforcement  # noqa: TC004

END_ZERO_TOLERANCE = 1e-3  # cm, zero-moment points this close to a beam end are ignored
MIN_SUPPORT_ANCHORAGE_LENGTH = 6.0  # cm, NBR 6118 - Section 18.3.2.4.1


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

        When the shifted point (center ∓ a_l) of a positive-moment point reaches a support's inner face, the support rules replace this extent (see ``_run_support_anchorage``).

        Args:
            available_space: Length from the section to the bar's end (cm).
            left: Whether to anchor towards the left; otherwise the right.
            allow_clamp: Whether clamps may complete the anchorage when the
                hooked bars do not fit.

        Returns:
            The clamps set on the layer, or None if the bars anchor without them.

        Raises:
            ValueError: If there isn't enough space even with hooks, and clamps are not allowed or not possible at that end; or if a reached support's checks fail.
        """
        self.left = left
        self.logging_info = f"{self.id} ({'Left' if self.left else 'Right'})"
        support_index = self._reached_support_index
        if support_index is not None:
            return self._run_support_anchorage(
                support_index, available_space, allow_clamp
            )

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
        return self._add_clamps(clamp_available_length, self.necessary_anchorage_length)

    def _add_clamps(
        self, clamp_available_length: float, necessary_length: float
    ) -> Clamps:
        """Choose the clamps for the current side and share them with the side's other layers

        One set of clamps serves every layer on a side. The current layer gets the chosen clamps, and so does every layer that already had clamps on this side, so a larger choice replaces the previous one.

        Args:
            clamp_available_length: Length available for the clamps (cm).
            necessary_length: Anchorage length the bars would need (cm).

        Returns:
            The clamps set on the side's layers.

        Raises:
            ValueError: Propagated from the clamp calculator if the reinforcement's effective depth or design shear is not set, or if no clamp arrangement fits.
        """
        clamps = self._build_clamp_calculator(
            clamp_available_length, necessary_length
        ).run()
        for layer in self.reinforcement.chosen_bars:
            if layer is self.layer or layer.get_clamps(self.left) is not None:
                layer.set_clamps(self.left, clamps)
        return clamps

    @property
    def _side_clamps(self) -> Clamps | None:
        """Return the clamps already set on the current side by any layer, or None"""
        for layer in self.reinforcement.chosen_bars:
            clamps = layer.get_clamps(self.left)
            if clamps is not None:
                return clamps
        return None

    def _build_clamp_calculator(
        self, clamp_available_length: float, necessary_length: float
    ) -> AnchorageClampCalculator:
        """Build the clamp calculator for the current side, with hooks enabled

        Args:
            clamp_available_length: Length inside the extremity support (cm).
            necessary_length: Anchorage length the hooked bars would need (cm).

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
            necessary_length=necessary_length,
            design_bond_strength=self.design_bond_strength,
            stirrup_inner_width=self.reinforcement.stirrup_inner_width,
            clamps_fit=self.reinforcement.clamps_fit,
            existing_clamps=self._side_clamps,
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
        return self._length_inside_support(self._extremity_support)

    def _length_inside_support(self, support: Support) -> float:
        """Return the length from a support's inner face to its outer face minus the effective covering (cm)"""
        effective_covering = self.reinforcement.effective_covering()  # cm
        length = (support.right - support.left) - effective_covering
        log_property(f"Available length inside the support = {length:.2f} cm")
        return length

    @property
    def _reached_support_index(self) -> int | None:
        """Find the support whose inner face the shifted point reaches on the current side

        Only the bars of a positive-moment point (``span_moment`` set) are checked. The shifted point A = center ∓ a_l reaches the nearest support on the current side when it lies on or past that support's inner face.

        Returns:
            Index of the support in ``beam.supports``, or None if A stays
            short of it.

        References:
            ABNT NBR 6118:2026 — Section 18.3.2.3.1
        """
        if self.reinforcement.span_moment is None:
            return None
        center = self.reinforcement.center_position  # cm
        supports = self.reinforcement.beam.supports
        if self.left:
            indices = [i for i, s in enumerate(supports) if s.center < center]
            if not indices:
                return None
            index = indices[-1]
            is_reached = center - self.moment_shift <= supports[index].right
        else:
            indices = [i for i, s in enumerate(supports) if s.center > center]
            if not indices:
                return None
            index = indices[0]
            is_reached = center + self.moment_shift >= supports[index].left
        return index if is_reached else None

    def _inner_face_distance(self, support: Support) -> float:
        """Return the distance from the section to the support's inner face (cm), zero inside the support"""
        center = self.reinforcement.center_position  # cm
        distance = center - support.right if self.left else support.left - center
        return max(distance, 0.0)

    def _run_support_anchorage(
        self, support_index: int, available_space: float, allow_clamp: bool
    ) -> Clamps | None:
        """Check a reached support and anchor the layer bars from its inner face

        Both support types check the area carried to the support, then anchor the bars past its inner face (see ``_run_inner_support_anchorage`` and ``_run_outer_support_anchorage``).

        Args:
            support_index: Index of the reached support in ``beam.supports``.
            available_space: Length from the section to the bar's end (cm),
                used for inner supports.
            allow_clamp: Whether clamps may complete the anchorage when the
                bars do not fit.

        Returns:
            The clamps set on the layer, or None if the bars anchor without them.

        Raises:
            ValueError: If a check fails, or if the bars do not fit (even with
                clamps, when allowed).

        References:
            ABNT NBR 6118:2026 — Sections 18.3.2.4 and 18.3.2.4.1
        """
        support = self.reinforcement.beam.supports[support_index]
        log_operation(
            f"Shifted point reaches the support at {support.center:.2f} cm; anchoring from its inner face."
        )
        self._check_support_area(support_index)
        face_distance = self._inner_face_distance(support)  # cm

        if support.is_extremity(self.reinforcement.beam.length):
            self._check_outer_support_force(support_index)
            return self._run_outer_support_anchorage(
                support, face_distance, allow_clamp
            )
        return self._run_inner_support_anchorage(
            face_distance, available_space, allow_clamp
        )

    def _run_inner_support_anchorage(
        self, face_distance: float, available_space: float, allow_clamp: bool
    ) -> Clamps | None:
        """Anchor the layer bars 10φ past an inner support's face

        Straight bars; when they do not fit before the bar's end and clamps are allowed, hooked bars take the whole available space and clamps carry the rest of the force.

        Args:
            face_distance: Distance from the section to the inner face (cm).
            available_space: Length from the section to the bar's end (cm).
            allow_clamp: Whether clamps may complete the anchorage.

        Returns:
            The clamps set on the layer, or None if the bars anchor without them.

        Raises:
            ValueError: If the bars do not fit, and clamps are not allowed or
                there is no length past the face for them.

        References:
            ABNT NBR 6118:2026 — Section 18.3.2.4.1
        """
        self.layer.set_hooks(self.left, False)
        past_face = 10 * (self.max_diameter / 10)  # cm
        length = face_distance + past_face  # cm
        if length <= available_space:
            self.layer.set_anchorage_length(length, self.left)
            log_operation(f"Anchorage length of {length:.2f} cm set (10φ past face).")
            return None

        # NOTE the code should not reach this normally
        error_message = f"Not enough space for 10φ past the inner support's face. Available: {available_space:.2f} cm, Required: {length:.2f} cm."
        if not allow_clamp:
            log_operation(error_message)
            raise ValueError(error_message)

        self.layer.set_hooks(self.left, True)
        hooked_space = self.get_adjusted_available_space_for_hooks(
            available_space
        )  # cm
        clamp_available_length = hooked_space - face_distance  # cm
        if clamp_available_length <= 0:
            error_message += " No length past the support's face for clamps."
            log_operation(error_message)
            raise ValueError(error_message)

        log_operation("Not enough space for 10φ past the face; Adding clamps...")
        self.layer.set_anchorage_length(hooked_space, self.left)
        return self._add_clamps(clamp_available_length, past_face)

    def _run_outer_support_anchorage(
        self, support: Support, face_distance: float, allow_clamp: bool
    ) -> Clamps | None:
        """Anchor the layer bars inside an outer support, from its inner face

        Needs max(l_b,nec, r + 5.5φ, 6 cm) inside the support: straight bars first, then hooked bars; when neither fits and clamps are allowed, hooked bars take the whole room and clamps carry the rest of the force.

        Args:
            support: The reached outer support.
            face_distance: Distance from the section to the inner face (cm).
            allow_clamp: Whether clamps may complete the anchorage.

        Returns:
            The clamps set on the layer, or None if the bars anchor without them.

        Raises:
            ValueError: If the hooked bars do not fit, and clamps are not
                allowed or there is no length inside the support for them.

        References:
            ABNT NBR 6118:2026 — Section 18.3.2.4.1
        """
        room = self._length_inside_support(support)  # cm
        for with_hooks in (False, True):
            self.layer.set_hooks(self.left, with_hooks)
            space = (
                self.get_adjusted_available_space_for_hooks(room)
                if with_hooks
                else room
            )  # cm
            past_face = self.outer_support_anchorage_length  # cm
            if past_face <= space:
                self.layer.set_anchorage_length(face_distance + past_face, self.left)
                hooks_state = "with hooks" if with_hooks else "without hooks"
                log_operation(
                    f"Anchorage length of {face_distance + past_face:.2f} cm set {hooks_state} ({past_face:.2f} cm past face)."
                )
                return None

        error_message = f"Not enough space inside the support - even with hooks. Available: {room:.2f} cm, Required: {past_face:.2f} cm."
        if not allow_clamp:
            log_operation(error_message)
            raise ValueError(error_message)
        if space <= 0:
            error_message += " No length inside the support for clamps."
            log_operation(error_message)
            raise ValueError(error_message)

        log_operation(
            "Not enough space inside the support with hooks; Adding clamps..."
        )
        self.layer.set_anchorage_length(face_distance + space, self.left)
        return self._add_clamps(room, past_face)

    def _check_support_area(self, support_index: int) -> None:
        """Check that the bars carried to the support cover part of the span's area

        A_s >= A_s,vão / 4 when the support moment is negative and |M_apoio| > 0.5 M_vão; otherwise A_s >= A_s,vão / 3.

        Args:
            support_index: Index of the reached support in ``beam.supports``.

        Raises:
            ValueError: If the reinforcement area is below that share.

        References:
            ABNT NBR 6118:2026 — Section 18.3.2.4-c
        """
        span_moment = cast(float, self.reinforcement.span_moment)  # kN.m
        support_moment = self.reinforcement.support_moment(support_index)  # kN.m
        is_large_negative = (
            support_moment < 0 and abs(support_moment) > 0.5 * span_moment
        )
        share = 1 / 4 if is_large_negative else 1 / 3
        span_area = cast(float, self.reinforcement.required_area)  # cm²
        required = share * span_area  # cm²
        provided = self.reinforcement.area  # cm²
        log_property(
            f"Support area check (M_apoio = {support_moment:.2f} kN.m, M_vão = {span_moment:.2f} kN.m): A_s = {provided:.3f} cm² >= {share:.3f} A_s,vão = {required:.3f} cm²"
        )
        if provided < required:
            error_message = f"Reinforcement at the support ({provided:.3f} cm²) is below {share:.3f} of the span's ({span_area:.3f} cm²)."
            log_operation(error_message)
            raise ValueError(error_message)

    def _check_outer_support_force(self, support_index: int) -> None:
        """Check that the bars resist the force to anchor at an outer support

        F_sd = M_Sd / z + (a_l / d) V_Sd >= (a_l / d) V_Sd, with z = d - y/2 and M_Sd positive when it tensions the bars; A_s >= F_sd / f_yd.

        Args:
            support_index: Index of the reached support in ``beam.supports``.

        Raises:
            ValueError: If d, y or V_Sd is not set, or if the reinforcement
                area is below F_sd / f_yd.

        References:
            ABNT NBR 6118:2026 — Section 18.3.2.4-b
        """
        effective_depth = self.reinforcement.effective_depth  # cm
        stress_block_depth = self.reinforcement.stress_block_depth  # cm
        design_shear = self.reinforcement.design_shear  # kN
        if (
            effective_depth is None
            or stress_block_depth is None
            or design_shear is None
        ):
            raise ValueError(
                "Effective depth, stress block depth and design shear must be set before the outer support check."
            )
        support_moment = self.reinforcement.support_moment(support_index)  # kN.m
        design_moment = design_effort_elu(support_moment * 100)  # kN.cm
        lever_arm = effective_depth - stress_block_depth / 2  # cm
        shear_force = (self.moment_shift / effective_depth) * design_shear  # kN
        force = max(design_moment / lever_arm, 0.0) + shear_force  # kN
        required = force / self.steel.fyd  # cm²
        provided = self.reinforcement.area  # cm²
        log_property(
            f"Outer support force (F_sd = M_Sd / z + (a_l / d) V_Sd) = {force:.2f} kN; A_s = {provided:.3f} cm² >= {required:.3f} cm²"
        )
        if provided < required:
            error_message = f"Reinforcement at the outer support ({provided:.3f} cm²) is below F_sd / f_yd ({required:.3f} cm²)."
            log_operation(error_message)
            raise ValueError(error_message)

    @property
    def outer_support_anchorage_length(self) -> float:
        """Calculate the anchorage length past an outer support's inner face

        The greatest of l_b,nec, r + 5.5φ (r: hook radius, half the bending pin diameter) and 6 cm.

        Returns:
            Length in cm.

        References:
            ABNT NBR 6118:2026 — Section 18.3.2.4.1
        """
        diameter_cm = self.max_diameter / 10  # cm
        hook_radius = self.steel.bend_pin_diameter(self.max_diameter) / 2  # cm
        length = max(
            self.necessary_anchorage_length,
            hook_radius + 5.5 * diameter_cm,
            MIN_SUPPORT_ANCHORAGE_LENGTH,
        )
        log_property(
            f"Outer support anchorage length (max(l_b,nec, r + 5.5φ, 6 cm)) = {length:.2f} cm"
        )
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
