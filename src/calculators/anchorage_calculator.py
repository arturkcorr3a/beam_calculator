from typing import TYPE_CHECKING, cast

from src.calculators.anchorage_clamp_calculator import (
    AnchorageClampCalculator,
    AnchorageClampCalculatorLabel,
)
from src.config import APP_CONFIG
from src.logger import log_operation, log_property, logger_label
from src.properties.steel import Steel
from src.reinforcement.anchorage_summary import AnchorageSummary
from src.reinforcement.clamps import Clamps
from src.reinforcement.staggering import nearest_distance
from src.structural_elements.rectangular_beam import RectangularBeam
from src.structural_elements.support import Support

if TYPE_CHECKING:
    from src.reinforcement.reinforcement import Reinforcement  # noqa: TC004

END_ZERO_TOLERANCE = 1e-3  # cm, zero-moment points this close to a beam end are ignored
MIN_SUPPORT_ANCHORAGE_LENGTH = 6.0  # cm, NBR 6118 - Section 18.3.2.4.1
_MM_PER_CM = 10.0


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
        self.layer_index = layer_index
        self.layer = reinforcement.chosen_bars[layer_index]
        self.reinforcement = reinforcement
        self.beam_height = self.reinforcement.beam.height  # cm
        self.id = id
        self.summaries: list[AnchorageSummary] = []  # one per anchored side

    def run(
        self, available_space: float, left: bool, allow_clamp: bool = False
    ) -> Clamps | None:
        """Check the available space and set the layer bars' anchorage lengths

        Tries straight bars first, then hooked bars. If both fail and clamps are allowed at an extremity support, the hooked bars take the whole
        available space and clamps carry the rest of the force.

        When the layer's shifted point A (center ∓ (l_A + a_l), see ``_reached_support_index``) of a positive-moment point reaches a support's inner face, the support rules replace this extent (see ``_run_support_anchorage``).

        Args:
            available_space: Length from the section to the bar's end (cm).
            left: Whether to anchor towards the left; otherwise the right.
            allow_clamp: Whether clamps may complete the anchorage when the
                hooked bars do not fit.

        Returns:
            The clamps set on the layer, or None if the bars anchor without them.

        Raises:
            ValueError: If there isn't enough space even with hooks, and clamps are not allowed or not possible at that end; if the hooks needed do not fit in the section height; or if a reached support's checks fail.
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
        self.check_hook_fits()
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
        clamps = self._add_clamps(
            clamp_available_length, self.necessary_anchorage_length
        )
        self._record()
        return clamps

    def run_end_support(self, left: bool) -> None:
        """Anchor the layer bars into the end support they are centered on

        Tensioned top bars (negative moment) run over the pillar to its outer face minus the covering, then bend down into it as a frame joint: D per Section 18.2.2 and a straight leg of l_b,nec (α = 0.7, hooked). The leg goes into the pillar, so the section height does not limit it. Other bars keep a standard hook at the support's center, which must fit in the section height.

        Args:
            left: Whether the support is on the left (x = 0); otherwise on the right (x = L).

        Raises:
            ValueError: If a standard hook does not fit in the section height.

        References:
            ABNT NBR 6118:2026 — Sections 9.4.2.5 and 18.2.2
            CARVALHO, ch. 5, example 4 (detailing of the frame joint)
        """
        self.left = left
        self.logging_info = f"{self.id} ({'Left' if self.left else 'Right'})"
        is_frame_joint = (
            self.reinforcement.is_tensioned
            and not self.reinforcement.is_bottom_reinforcement
        )
        if not is_frame_joint:
            self.check_hook_fits()
            self.layer.set_hooks(self.left, True)
            self.layer.set_anchorage_length(0.0, self.left)
            self._record()
            return

        self.layer.set_hooks(self.left, True)  # l_b,nec with α = 0.7
        leg_length = self.necessary_anchorage_length  # cm
        self.layer.set_frame_joint_hooks(self.left, leg_length)

        support = self._extremity_support
        center = self.reinforcement.center_position  # cm
        outer_face_distance = (
            center - support.left if self.left else support.right - center
        )  # cm
        horizontal_length = max(
            self.get_adjusted_available_space_for_hooks(
                outer_face_distance - RectangularBeam.nominal_covering
            ),
            0.0,
        )  # cm
        self.layer.set_anchorage_length(horizontal_length, self.left)
        bend_diameter = self.steel.frame_joint_bend_diameter(self.max_diameter)  # cm
        log_property(
            f"Frame joint hook: D = {bend_diameter:.2f} cm; leg (l_b,nec) = {leg_length:.2f} cm"
        )
        log_operation(
            f"Anchorage length of {horizontal_length:.2f} cm set over the end support, bent into it as a frame joint."
        )
        self._record()

    def support_anchorage_length(self, support_index: int, left: bool) -> float:
        """Calculate the bar length past the section needed to anchor inside a support

        The distance to the support's inner face plus the anchorage past it: 10φ at an intermediate support; at an end support, the greatest of l_b,nec, r + 5.5φ and 6 cm, with the layer's current hooks.

        Args:
            support_index: Index of the support in ``beam.supports``.
            left: Whether the support is on the left of the section; otherwise on the right.

        Returns:
            Length in cm.

        References:
            ABNT NBR 6118:2026 — Section 18.3.2.4.1
        """
        self.left = left
        self.logging_info = f"{self.id} ({'Left' if self.left else 'Right'})"
        support = self.reinforcement.beam.supports[support_index]
        face_distance = self._inner_face_distance(support)  # cm
        if support.is_extremity(self.reinforcement.beam.length):
            return face_distance + self.outer_support_anchorage_length
        return face_distance + 10 * (self.max_diameter / 10)

    def anchor_into_support(
        self,
        support_index: int,
        available_space: float,
        left: bool,
        allow_clamp: bool,
    ) -> Clamps | None:
        """Anchor the layer bars inside a support, from its inner face

        Uses the same anchorage rules as a shifted point that reaches the support (see ``_run_inner_support_anchorage`` and ``_run_outer_support_anchorage``), whether or not it does.

        Args:
            support_index: Index of the support in ``beam.supports``.
            available_space: Length from the section to the bar's end (cm),
                used for intermediate supports.
            left: Whether the support is on the left of the section; otherwise on the right.
            allow_clamp: Whether clamps may complete the anchorage when the
                bars do not fit.

        Returns:
            The clamps set on the layer, or None if the bars anchor without them.

        Raises:
            ValueError: If the bars do not fit inside the support, even with
                clamps when allowed.

        References:
            ABNT NBR 6118:2026 — Section 18.3.2.4.1
        """
        self.left = left
        self.logging_info = f"{self.id} ({'Left' if self.left else 'Right'})"
        return self._run_support_anchorage(support_index, available_space, allow_clamp)

    def _record(self) -> None:
        """Keep the anchorage lengths of the side just anchored, with its final hooks"""
        self.summaries.append(
            AnchorageSummary(
                layer_index=self.layer.layer_index,
                side="left" if self.left else "right",
                basic_length=self.basic_anchorage_length,
                necessary_length=self.necessary_anchorage_length,
            )
        )

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

        Only the bars of a positive-moment point (``span_moment`` set) are checked. The layer's anchorage starts at the point where its stress begins to fall (see ``stress_start_distance``); shifted by a_l, it reaches the nearest support on the current side when it lies on or past that support's inner face.

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
        shift = self.stress_start_distance + self.moment_shift  # cm
        if self.left:
            indices = [i for i, s in enumerate(supports) if s.center < center]
            if not indices:
                return None
            index = indices[-1]
            is_reached = center - shift <= supports[index].right
        else:
            indices = [i for i, s in enumerate(supports) if s.center > center]
            if not indices:
                return None
            index = indices[0]
            is_reached = center + shift >= supports[index].left
        return index if is_reached else None

    def _inner_face_distance(self, support: Support) -> float:
        """Return the distance from the section to the support's inner face (cm), zero inside the support"""
        center = self.reinforcement.center_position  # cm
        distance = center - support.right if self.left else support.left - center
        return max(distance, 0.0)

    def _run_support_anchorage(
        self, support_index: int, available_space: float, allow_clamp: bool
    ) -> Clamps | None:
        """Anchor the layer bars from a reached support's inner face

        Both support types anchor the bars past the inner face (see ``_run_inner_support_anchorage`` and ``_run_outer_support_anchorage``). The areas carried to the supports are checked after the reinforcement is chosen (see ``carry_span_bars_to_supports`` and ``anchor_outer_supports``).

        Args:
            support_index: Index of the reached support in ``beam.supports``.
            available_space: Length from the section to the bar's end (cm),
                used for inner supports.
            allow_clamp: Whether clamps may complete the anchorage when the
                bars do not fit.

        Returns:
            The clamps set on the layer, or None if the bars anchor without them.

        Raises:
            ValueError: If the bars do not fit (even with clamps, when allowed).

        References:
            ABNT NBR 6118:2026 — Section 18.3.2.4.1
        """
        support = self.reinforcement.beam.supports[support_index]
        log_operation(
            f"Anchoring into the support at {support.center:.2f} cm from its inner face."
        )
        face_distance = self._inner_face_distance(support)  # cm

        if support.is_extremity(self.reinforcement.beam.length):
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
            ValueError: If the bars do not fit, and clamps are not allowed,
                the hooks do not fit in the section height, or there is no
                length past the face for them.

        References:
            ABNT NBR 6118:2026 — Section 18.3.2.4.1
        """
        self.layer.set_hooks(self.left, False)
        past_face = 10 * (self.max_diameter / 10)  # cm
        length = face_distance + past_face  # cm
        if length <= available_space:
            self.layer.set_anchorage_length(length, self.left)
            log_operation(f"Anchorage length of {length:.2f} cm set (10φ past face).")
            self._record()
            return None

        # NOTE the code should not reach this normally
        error_message = f"Not enough space for 10φ past the inner support's face. Available: {available_space:.2f} cm, Required: {length:.2f} cm."
        if not allow_clamp:
            log_operation(error_message)
            raise ValueError(error_message)

        self.check_hook_fits()
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
        clamps = self._add_clamps(clamp_available_length, past_face)
        self._record()
        return clamps

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
            ValueError: If the straight bars do not fit and the hooks do not
                fit in the section height; or if the hooked bars do not fit,
                and clamps are not allowed or there is no length inside the
                support for them.

        References:
            ABNT NBR 6118:2026 — Section 18.3.2.4.1
        """
        room = self._length_inside_support(support)  # cm
        for with_hooks in (False, True):
            if with_hooks:
                self.check_hook_fits()
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
                self._record()
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
        clamps = self._add_clamps(room, past_face)
        self._record()
        return clamps

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
            self._record()
            return True
        return False

    @property
    def total_anchorage_length(self) -> float:
        """Calculate the bar length past the section

        The greatest of l_b,nec past the point where the layer's stress starts to fall and the length past the layer's theoretical cut point (see ``length_past_cut_point``), plus the moment shift a_l. Unstaggered bars start falling at the section itself.

        Returns:
            Length in cm.

        References:
            ABNT NBR 6118:2026 — Section 18.3.2.3.1 (Figure 18.3)
        """
        # PAPER get ref
        total = (
            max(
                self.stress_start_distance + self.necessary_anchorage_length,
                self.length_past_cut_point,
            )
            + self.moment_shift
        )
        log_property(
            f"Total Anchorage Length (max(l_A + l_b,nec, l_B + 10φ) + a_l) = {total:.2f} cm"
        )
        return total

    @property
    def stress_start_distance(self) -> float:
        """Calculate the distance from the section to where the layer's stress starts to fall, on the current side

        That is where the moment diagram drops to the top of the layer's band (see ``Reinforcement.layer_moment_band``). It is zero for the innermost layer, whose band ends at the section moment, and for unstaggered bars. When the diagram does not reach the band's top before the zero-moment point, the cut point's distance is used.

        Returns:
            Length in cm.

        References:
            ABNT NBR 6118:2026 — Section 18.3.2.3.1 (Figure 18.3, point A)
        """
        band = self.reinforcement.layer_moment_band(self.layer_index)
        if band is None:
            return 0.0
        _, upper = band  # kN.m
        distance = self._moment_level_distance(upper)  # cm
        if distance is None:
            distance = self._cut_point_distance or 0.0
        log_property(
            f"Distance to the start of the stress drop (l_A) = {distance:.2f} cm"
        )
        return distance

    @property
    def length_past_cut_point(self) -> float:
        """Calculate the length from the section to 10φ past the layer's theoretical cut point, on the current side

        The cut point is where the moment diagram drops to the bottom of the layer's band (see ``Reinforcement.layer_moment_band``). For the first layer and for unstaggered bars it is the nearest zero-moment point; zero-moment points at the beam ends are ignored.

        Returns:
            Length in cm; zero when there is no cut point inside the beam on the
            current side.

        References:
            ABNT NBR 6118:2026 — Section 18.3.2.3.1 (Figure 18.3, point B)
        """
        distance = self._cut_point_distance  # cm
        if distance is None:
            return 0.0
        length = distance + 10 * (self.max_diameter / 10)
        log_property(f"Length to the cut point + 10φ (l_B + 10φ) = {length:.2f} cm")
        return length

    @property
    def _cut_point_distance(self) -> float | None:
        """Return the distance from the section to the layer's theoretical cut point on the current side (cm), or None"""
        band = self.reinforcement.layer_moment_band(self.layer_index)
        if band is not None and band[0] != 0.0:
            distance = self._moment_level_distance(band[0])  # cm
            if distance is not None:
                return distance
        return self._zero_moment_distance

    def _moment_level_distance(self, level: float) -> float | None:
        """Return the distance from the section to where the moment diagram drops to a level, on the current side

        Only positions up to the nearest zero-moment point on that side count.

        Args:
            level: Characteristic bending moment (kN.m), with the section moment's sign.

        Returns:
            Distance in cm: zero when the level is the section moment or above it; None when the diagram does not reach it.
        """
        section_moment = self.reinforcement.section_moment  # kN.m
        moment_positions = self.reinforcement.moment_positions
        if section_moment is None or moment_positions is None:
            return None
        if abs(level) >= abs(section_moment):
            return 0.0
        return nearest_distance(
            self.reinforcement.center_position,
            moment_positions(level),
            self.left,
            limit=self._zero_moment_distance,
        )

    @property
    def _zero_moment_distance(self) -> float | None:
        """Return the distance from the section to the nearest zero-moment point inside the beam on the current side (cm), or None

        Zero-moment points at the beam ends are ignored.
        """
        beam_length = self.reinforcement.beam.length  # cm
        inner_zeros = [
            zero
            for zero in self.reinforcement.moment_zeros
            if END_ZERO_TOLERANCE < zero < beam_length - END_ZERO_TOLERANCE
        ]
        return nearest_distance(
            self.reinforcement.center_position, inner_zeros, self.left
        )

    @staticmethod
    def adherence_coefficient_for(good_adherence: bool) -> float:
        """Return the bond zone coefficient η2: 1.0 in a good bond zone, 0.7 in a poor one

        References:
            ABNT NBR 6118:2026 — Section 9.3.2.1
        """
        return 1.0 if good_adherence else 0.7

    @staticmethod
    def diameter_coefficient_for(diameter_mm: float) -> float:
        """Return the bar diameter coefficient η3: 1.0 up to 32 mm, (132 − φ)/100 above

        Args:
            diameter_mm: Bar diameter φ (mm).

        References:
            ABNT NBR 6118:2026 — Section 9.3.2.1
        """
        return min((132 - diameter_mm) / 100, 1.00)

    @staticmethod
    def design_bond_strength_for(
        diameter_mm: float, steel: Steel, good_adherence: bool
    ) -> float:
        """Return the design bond strength f_bd (kN/cm²) of a bar in the pavement concrete

        Args:
            diameter_mm: Bar diameter φ (mm).
            good_adherence: Whether the bar sits in a good bond zone (Section 9.3.1).

        References:
            ABNT NBR 6118:2026 — Section 9.3.2.1
        """
        return (
            steel.bond_coefficient
            * AnchorageCalculator.adherence_coefficient_for(good_adherence)
            * AnchorageCalculator.diameter_coefficient_for(diameter_mm)
            * APP_CONFIG.pavement_concrete.fctd
        )

    @staticmethod
    def basic_anchorage_length_for(
        diameter_mm: float, steel: Steel, bond_strength: float
    ) -> float:
        """Return the basic anchorage length l_b (cm), at least 25 bar diameters

        Args:
            diameter_mm: Bar diameter φ (mm).
            bond_strength: Design bond strength f_bd (kN/cm²).

        References:
            ABNT NBR 6118:2026 — Section 9.4.2.4
        """
        diameter_cm = diameter_mm / _MM_PER_CM
        return max(25 * diameter_cm, (diameter_cm / 4) * (steel.fyd / bond_strength))

    @staticmethod
    def min_anchorage_length_for(basic_length: float, diameter_mm: float) -> float:
        """Return the minimum anchorage length l_b,min (cm): the greatest of 0.3 l_b, 10φ and 10 cm

        Args:
            basic_length: Basic anchorage length l_b (cm).
            diameter_mm: Bar diameter φ (mm).

        References:
            ABNT NBR 6118:2026 — Section 9.4.2.5
        """
        return max(0.3 * basic_length, 10 * (diameter_mm / _MM_PER_CM), 10)

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
        eta_2 = self.adherence_coefficient_for(layer_has_good_adherence)

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
        eta_3 = self.diameter_coefficient_for(self.max_diameter)
        log_property(f"Diameter Coefficient (eta_3) = {eta_3:.4f}")
        return eta_3

    @property
    def basic_anchorage_length(self) -> float:
        """Calculate the basic anchorage length (l_b) in cm, based on NBR 6118 - Section 9.4.2.4"""
        l_b = self.basic_anchorage_length_for(
            self.max_diameter, self.steel, self.design_bond_strength
        )
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
        l_b_min = self.min_anchorage_length_for(
            self.basic_anchorage_length, self.max_diameter
        )
        log_property(f"Minimum Anchorage Length (l_b,min) = {l_b_min:.2f} cm")
        return l_b_min

    def check_hook_fits(self) -> None:
        """Check that the layer's 90° hooks fit in the section height

        The hook's leg runs from the bars' axis towards the opposite face and must stop at the nominal covering. The room is h − y − c_nom for bottom bars and y − c_nom for top bars, with y the layer's centroid from the bottom face.

        Raises:
            ValueError: If the tallest hook in the layer (D/2 + φ/2 + 8φ) is
                higher than the room.

        References:
            ABNT NBR 6118:2026 — Section 9.4.2.3
        """
        y_centroid = self.layer.y_centroid_position  # cm
        distance_to_opposite_face = (
            self.beam_height - y_centroid
            if self.reinforcement.is_bottom_reinforcement
            else y_centroid
        )  # cm
        room = distance_to_opposite_face - RectangularBeam.nominal_covering  # cm
        hook_height = max(bar.hook_height for bar in self.layer.bars)  # cm
        log_property(
            f"Hook height (D/2 + φ/2 + 8φ) = {hook_height:.2f} cm; room in the section = {room:.2f} cm"
        )
        if hook_height > room:
            error_message = f"Hooks do not fit in the section height. Hook height: {hook_height:.2f} cm, Room: {room:.2f} cm."
            log_operation(error_message)
            raise ValueError(error_message)

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
