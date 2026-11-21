from collections import Counter
from collections.abc import Callable, Sequence
from copy import copy
from itertools import pairwise
from typing import cast

from src.calculators.anchorage_calculator import AnchorageCalculator
from src.config import APP_CONFIG
from src.errors import (
    EnginePreconditionError,
    MaxLayersExceededError,
    NoReinforcementLayoutError,
)
from src.logger import (
    log_element,
    log_iteration,
    log_operation,
    log_property,
    logger_label,
)
from src.reinforcement.anchorage_summary import AnchorageSummary
from src.reinforcement.layer import Layer
from src.reinforcement.rebar_chooser import RebarChooser
from src.reinforcement.staggering import MomentBand, layer_moment_bands
from src.structural_elements.rebar import Rebar
from src.structural_elements.rectangular_beam import RectangularBeam

DEFAULT_DISTANCE_FOR_D_CALCULATION = 1.0  # cm
DEFAULT_STIRRUP_DIAMETER_FOR_D_CALCULATION = 1.0  # cm
END_SUPPORT_TOLERANCE = 1e-3  # cm
# Buildable options within this fraction of the smallest buildable area are tied
AREA_TOLERANCE_RATIO = 0.05


@logger_label("Longitudinal Reinforcement - {id}")
class Reinforcement:
    """
    Defines the longitudinal reinforcement, by layer.
    """

    required_area: float | None = None  # cm², to be calculated

    def __init__(
        self,
        beam: RectangularBeam,
        is_bottom_reinforcement: bool,
        center_position: float,
        id: str = "",
        moment_zeros: tuple[float, ...] = (),
        support_moments: tuple[float, ...] = (),
        span_moment: float | None = None,
        is_tensioned: bool = True,
        anchored_support: int | None = None,
        stacked_on: Reinforcement | None = None,
        section_moment: float | None = None,
        moment_positions: Callable[[float], Sequence[float]] | None = None,
    ):
        """Initialize an empty longitudinal reinforcement

        Args:
            beam: Rectangular beam section.
            is_bottom_reinforcement: Whether the bars sit on the bottom face.
            center_position: Position of the interest point along the beam (cm).
            moment_zeros: Positions along the beam where the bending moment is
                zero (cm), used for the bars' anchorage.
            support_moments: Characteristic bending moment on each of the beam's
                supports (kN.m), aligned with ``beam.supports``; missing ones
                are read as zero.
            span_moment: Characteristic positive moment of the span (kN.m). Set
                only on the bottom bars of a positive-moment point; enables the
                support anchorage checks.
            is_tensioned: Whether the bars are tensioned; False for the
                compressed reinforcement.
            anchored_support: Index in ``beam.supports`` of the support whose
                inner face the point sits on; the bars are anchored inside it
                from the face on that side. None for an ordinary point.
            stacked_on: Reinforcement whose layers come first on the same face;
                this one's layers are stacked after its last non-empty layer.
            section_moment: Characteristic bending moment the bars were designed
                for (kN.m), signed. With ``moment_positions``, it staggers the
                tensioned bars by layer (see ``layer_moment_band``).
            moment_positions: Returns the positions along the beam (cm) where the
                characteristic bending moment equals a given value (kN.m).

        Raises:
            MaxLayersExceededError: If ``stacked_on`` already fills every layer.
        """
        self.beam = beam
        self.steel = beam.steel
        self.anchored_support = anchored_support
        self.stacked_on = stacked_on
        self.first_layer_index = (
            stacked_on.used_layers_top_index if stacked_on is not None else 0
        )
        if self.first_layer_index >= APP_CONFIG.max_layers:
            raise MaxLayersExceededError(
                f"No layer left to stack bars on: {self.first_layer_index} of {APP_CONFIG.max_layers} layers already used.",
                max_layers=APP_CONFIG.max_layers,
            )
        self.chosen_bars: tuple[Layer, ...] = self._build_empty_layers()
        self.is_chosen = False
        self.rebar_choice_options: tuple[tuple[Rebar, ...], ...] = ()
        self.is_bottom_reinforcement = is_bottom_reinforcement
        self.is_tensioned = is_tensioned
        self.center_position = center_position
        self.moment_zeros = moment_zeros  # cm, positions where M = 0
        self.support_moments = support_moments  # kN.m, characteristic, signed
        self.span_moment = span_moment  # kN.m, characteristic, M_vão
        self.section_moment = section_moment  # kN.m, characteristic, signed
        self.moment_positions = moment_positions
        self.moment_shift: float | None = None  # cm, a_l
        self.stirrup_diameter: float | None = None  # cm
        self.effective_depth: float | None = None  # cm, d, used by clamps
        self.stress_block_depth: float | None = None  # cm, y, used by supports
        self.design_shear: float | None = None  # kN, V_d, used by clamps
        self.anchorages: tuple[AnchorageSummary, ...] = ()  # of the chosen bars
        self._layout_anchorages: tuple[AnchorageSummary, ...] = ()  # last layout
        self.id = id

    def support_moment(self, support_index: int) -> float:
        """Return the characteristic moment on a support (kN.m), zero if not given"""
        if support_index < len(self.support_moments):
            return self.support_moments[support_index]
        return 0.0

    @property
    def is_staggered(self) -> bool:
        """Whether the bars are staggered by layer along the moment diagram

        Only tensioned bars with a section moment and a moment diagram are staggered.
        """
        return (
            self.is_tensioned
            and self.section_moment is not None
            and self.moment_positions is not None
        )

    def layer_moment_band(self, layer_index: int) -> MomentBand | None:
        """Return the band of the section moment a layer's bars resist, or None if not staggered

        The section moment is split among the non-empty layers in proportion to their areas: the first layer takes the band from zero moment up and is the longest, the innermost one takes the band ending at the section moment and is the shortest.

        Args:
            layer_index: Index of a non-empty chosen layer.

        Returns:
            The (lower, upper) characteristic moments of the band (kN.m), signed.

        Raises:
            EnginePreconditionError: If the layer has no bars.

        References:
            ABNT NBR 6118:2026 — Section 18.3.2.3.1 (Figure 18.3)
            Carvalho e Figueiredo Filho (2014) — Chapter 5, staggering of the longitudinal bars.
        """
        if not self.is_staggered:
            return None
        if not self.chosen_bars[layer_index].bars:
            raise EnginePreconditionError(f"Layer {layer_index} has no bars.")
        indexes = [i for i, layer in enumerate(self.chosen_bars) if layer.bars]
        bands = layer_moment_bands(
            [self.chosen_bars[i].area for i in indexes],
            cast(float, self.section_moment),
        )
        return bands[indexes.index(layer_index)]

    @property
    def used_layers_top_index(self) -> int:
        """Return the face's layer index just after this reinforcement's last non-empty layer

        Counts the layers of the reinforcement it is stacked on, if any.
        """
        used = sum(1 for layer in self.chosen_bars if layer.bars)
        return self.first_layer_index + used

    def _build_empty_layers(self) -> tuple[Layer, ...]:
        """Build the empty layers, up to the configured maximum on the face

        A stacked reinforcement gets only the layers left after its base's.
        """
        return tuple(
            Layer([], i) for i in range(APP_CONFIG.max_layers - self.first_layer_index)
        )  # list of chosen rebar sizes per layer

    def set_required_area(self, required_area: float) -> None:
        self.required_area = required_area
        self.choose()

    def choose(self) -> None:
        """Choose the bars for the required area

        Options that anchor without clamps are always preferred. Only if none
        of them can be anchored, a second pass allows clamps at the extremity
        supports.

        Raises:
            EnginePreconditionError: If the required area or moment shift is not set, or if
                clamps are needed but the effective depth or design shear is not
                set.
            NoReinforcementLayoutError: If no option can be laid out and
                anchored, even with clamps.
        """
        log_operation(
            f"Choosing reinforcement for required area: {self.required_area:.2f} cm²"
        )
        if self.required_area is None:
            raise EnginePreconditionError(
                "Required area must be set before choosing reinforcement."
            )
        if self.moment_shift is None:
            raise EnginePreconditionError(
                "Moment shift must be set before choosing reinforcement."
            )

        self.rebar_choice_options = RebarChooser.instance().ranked_solutions(
            self.steel, self.required_area
        )

        best_layers = self._select_best_layers(allow_clamp=False)
        if best_layers is None:
            log_operation(
                "No combination anchors without clamps; retrying allowing clamps."
            )
            if self.effective_depth is None or self.design_shear is None:
                self.clear_chosen_bars()
                raise EnginePreconditionError(
                    "Effective depth and design shear must be set before allowing clamps."
                )
            best_layers = self._select_best_layers(allow_clamp=True)
        if best_layers is None:
            self.clear_chosen_bars()
            raise NoReinforcementLayoutError()

        self.chosen_bars = best_layers
        self.is_chosen = True
        all_bars = [bar for layer in self.chosen_bars for bar in layer.bars]
        counter = Counter(int(b.diameter_mm) for b in all_bars)
        bar_desc = ", ".join(
            f"{count}x{d}mm" for d, count in sorted(counter.items(), reverse=True)
        )
        log_element(
            f"Bars chosen for required area {self.required_area:.2f} cm2: {bar_desc}"
        )

    def _select_best_layers(self, allow_clamp: bool) -> tuple[Layer, ...] | None:
        """Pick the best buildable option among the ranked choices

        The best option's anchorage summaries are kept in ``anchorages``.

        Args:
            allow_clamp: Whether clamps may complete the anchorage at the
                extremity supports.

        Returns:
            The laid-out layers of the best option, or None if no option fits.
        """
        # Options come sorted by area: the first buildable one sets the band, and within it fewer layers, then fewer bars, win
        best_layers: tuple[Layer, ...] | None = None
        best_key: tuple[int, int, float] | None = None
        best_anchorages: tuple[AnchorageSummary, ...] = ()
        threshold_area = float("inf")  # cm², set by the first buildable option
        for option in self.rebar_choice_options:
            option_area = sum(bar.area_cm2 for bar in option)  # cm²
            if option_area > threshold_area:
                break

            is_buildable = self._try_layout(option, allow_clamp)
            if not is_buildable:
                continue

            is_first_buildable = best_layers is None
            if is_first_buildable:
                threshold_area = option_area * (1 + AREA_TOLERANCE_RATIO)

            layers_used = sum(1 for layer in self.chosen_bars if layer.bars)
            key = (layers_used, len(option), option_area)
            if best_key is None or key < best_key:
                best_layers, best_key = self.chosen_bars, key
                best_anchorages = self._layout_anchorages
        self.anchorages = best_anchorages
        return best_layers

    def _try_layout(self, option: tuple[Rebar, ...], allow_clamp: bool) -> bool:
        """Lay out an option on fresh layers and check spacing and anchorage

        Args:
            option: Bars to lay out.
            allow_clamp: Whether clamps may complete the anchorage at the
                extremity supports.

        Returns:
            Whether the option fits; on failure the layers are left empty.
        """
        combo_label = ", ".join(f"{bar.diameter_mm}mm" for bar in option)
        log_iteration(f"Trying reinforcement combination: {combo_label}")
        self.clear_chosen_bars()
        try:
            self.distribute_bars_in_layers(list(option))
            self.arrange_bars()
            self._update_layers_y_centroids()
            self._run_anchorage_calculation(allow_clamp)
        except ValueError:
            log_iteration(
                "Combination failed due to spacing or anchorage constraints. Trying next combination."
            )
            self.clear_chosen_bars()
            return False
        log_iteration(f"Combination successful: {combo_label}")
        return True

    @property
    def _is_at_beam_start(self) -> bool:
        """Whether the reinforcement is centered on the beam's start support (x = 0)."""
        return self.center_position <= END_SUPPORT_TOLERANCE

    @property
    def _is_at_beam_end(self) -> bool:
        """Whether the reinforcement is centered on the beam's end support (x = L)."""
        return self.center_position >= self.beam.length - END_SUPPORT_TOLERANCE

    def _run_anchorage_calculation(self, allow_clamp: bool) -> None:
        """Run the anchorage calculation for each layer, setting the bars' lengths

        Bars centered on an end support are anchored towards the beam interior as usual, and hooked into the support on the other side (see ``AnchorageCalculator.run_end_support``): tensioned top bars run to the support's outer face and bend into it as a frame joint; other bars keep a standard hook with zero length.

        Args:
            allow_clamp: Whether clamps may complete the anchorage at the
                extremity supports.

        Raises:
            AnchorageLengthError: Propagated from the anchorage calculator if there isn't enough space for anchorage, even after adding hooks (and clamps, when allowed).
            HookDoesNotFitError: Propagated from the anchorage calculator if the standard hooks do not fit in the section height.
        """
        log_operation("Running anchorage calculation for chosen reinforcement layers.")
        moment_shift = cast(float, self.moment_shift)
        self._layout_anchorages = ()
        summaries: list[AnchorageSummary] = []
        for layer_index, layer in enumerate(self.chosen_bars):
            if len(layer.bars) == 0:
                continue
            anchorage_calculator = AnchorageCalculator(
                reinforcement=self,
                moment_shift=moment_shift,
                steel=self.steel,
                layer_index=layer_index,
                id=f"{self.id} | Layer {layer_index}",
            )

            if self._anchored_support_is_on(left=True):
                anchorage_calculator.anchor_into_support(
                    cast(int, self.anchored_support),
                    self._available_space(left=True),
                    left=True,
                    allow_clamp=allow_clamp,
                )
            elif self._is_at_beam_start:
                anchorage_calculator.run_end_support(left=True)
            else:
                anchorage_calculator.run(
                    self._available_space(left=True),
                    left=True,
                    allow_clamp=allow_clamp,
                )

            if self._anchored_support_is_on(left=False):
                anchorage_calculator.anchor_into_support(
                    cast(int, self.anchored_support),
                    self._available_space(left=False),
                    left=False,
                    allow_clamp=allow_clamp,
                )
            elif self._is_at_beam_end:
                anchorage_calculator.run_end_support(left=False)
            else:
                anchorage_calculator.run(
                    self._available_space(left=False),
                    left=False,
                    allow_clamp=allow_clamp,
                )
            summaries.extend(anchorage_calculator.summaries)
        self._layout_anchorages = tuple(summaries)
        if self.is_staggered:
            self._enforce_staggered_lengths()

    def _enforce_staggered_lengths(self) -> None:
        """Lengthen each layer's bars to at least the length of the layer above them

        Keeps the first layer the longest and the innermost one the shortest on each side, even where a layer's own anchorage would be longer than the one below it (a poorer bond zone, or hooks on the layer below). The new length is capped by the space up to the bar's end, less the hook cover when the bars are hooked on that side. Sides over an end support, anchored in the point's own support, or completed by clamps are left as they are.
        """
        indexes = [i for i, layer in enumerate(self.chosen_bars) if layer.bars]
        for left in (True, False):
            is_end_support = self._is_at_beam_start if left else self._is_at_beam_end
            if is_end_support or self._anchored_support_is_on(left):
                continue
            for lower_index, upper_index in reversed(list(pairwise(indexes))):
                lower = self.chosen_bars[lower_index]
                upper = self.chosen_bars[upper_index]
                if lower.get_clamps(left) is not None:
                    continue
                if upper.get_clamps(left) is not None:
                    continue
                current = _side_length(lower, left)  # cm
                target = min(
                    _side_length(upper, left),
                    self._side_length_limit(lower_index, left),
                )  # cm
                if target <= current:
                    continue
                lower.set_anchorage_length(target, left)
                log_operation(
                    f"Layer {lower_index} lengthened on the {'left' if left else 'right'} from {current:.2f} to {target:.2f} cm, to stay at least as long as layer {upper_index}."
                )

    def _side_length_limit(self, layer_index: int, left: bool) -> float:
        """Return the longest a layer's bars may run on one side (cm)

        The space up to the beam's end, less the hook cover when the bars are hooked on that side.

        References:
            ABNT NBR 6118:2026 — Section 9.4.2.5
        """
        space = self._available_space(left)  # cm
        layer = self.chosen_bars[layer_index]
        is_hooked = any(
            bar.left_hook_enabled if left else bar.right_hook_enabled
            for bar in layer.bars
        )
        if not is_hooked:
            return space
        calculator = self._layer_anchorage_calculator(layer_index)
        return calculator.get_adjusted_available_space_for_hooks(space)

    def _anchored_support_is_on(self, left: bool) -> bool:
        """Whether the support the point sits on lies on the given side of it"""
        if self.anchored_support is None:
            return False
        support = self.beam.supports[self.anchored_support]
        return (support.center < self.center_position) == left

    def _available_space(self, left: bool) -> float:
        """Return the length from the section to the beam's end minus the nominal covering (cm)

        Args:
            left: Whether to measure towards the left end; otherwise the right.
        """
        covering = RectangularBeam.nominal_covering  # cm
        if left:
            return self.center_position - covering
        return self.beam.length - covering - self.center_position

    def _layer_anchorage_calculator(self, layer_index: int) -> AnchorageCalculator:
        """Build the anchorage calculator of one chosen layer

        Raises:
            EnginePreconditionError: If the moment shift is not set.
        """
        if self.moment_shift is None:
            raise EnginePreconditionError(
                "Moment shift must be set before anchoring the bars."
            )
        return AnchorageCalculator(
            reinforcement=self,
            moment_shift=self.moment_shift,
            steel=self.steel,
            layer_index=layer_index,
            id=f"{self.id} | Layer {layer_index}",
        )

    def layer_reaches_support(
        self, layer_index: int, support_index: int, left: bool
    ) -> bool:
        """Check whether a layer's bars are anchored inside a support

        The bars reach the support when their length on that side covers the anchorage inside it (see ``AnchorageCalculator.support_anchorage_length``), or when clamps complete their anchorage on that side.

        Args:
            layer_index: Index of a non-empty chosen layer.
            support_index: Index of the support in ``beam.supports``.
            left: Whether the support is on the left of the center; otherwise on the right.

        Raises:
            EnginePreconditionError: If the layer has no bars or the moment shift is not set.

        References:
            ABNT NBR 6118:2026 — Section 18.3.2.4.1
        """
        layer = self.chosen_bars[layer_index]
        if not layer.bars:
            raise EnginePreconditionError(f"Layer {layer_index} has no bars.")
        if layer.get_clamps(left) is not None:
            return True  # clamps are only set where the bars end anchored in a support
        calculator = self._layer_anchorage_calculator(layer_index)
        needed = calculator.support_anchorage_length(support_index, left)  # cm
        length = max(
            bar.left_length if left else bar.right_length for bar in layer.bars
        )  # cm
        return length >= needed - END_SUPPORT_TOLERANCE

    def extend_layer_to_support(
        self, layer_index: int, support_index: int, left: bool
    ) -> None:
        """Extend a layer's bars into a support and anchor them there

        The layer's anchorage on that side is replaced: its clamps on that side are dropped, the bars are anchored from the support's inner face, and the side's anchorage summary is updated. Clamps are allowed only when the effective depth and design shear are set.

        Args:
            layer_index: Index of a non-empty chosen layer.
            support_index: Index of the support in ``beam.supports``.
            left: Whether the support is on the left of the center; otherwise on the right.

        Raises:
            EnginePreconditionError: If the moment shift is not set.
            AnchorageError: Propagated from the anchorage calculator if the bars cannot be anchored inside the support.

        References:
            ABNT NBR 6118:2026 — Sections 18.3.2.4-c and 18.3.2.4.1
        """
        layer = self.chosen_bars[layer_index]
        layer.set_clamps(left, None)
        calculator = self._layer_anchorage_calculator(layer_index)
        allow_clamp = self.effective_depth is not None and self.design_shear is not None
        calculator.anchor_into_support(
            support_index, self._available_space(left), left, allow_clamp
        )
        side = "left" if left else "right"
        kept = [
            summary
            for summary in self.anchorages
            if not (summary.layer_index == layer_index and summary.side == side)
        ]
        self.anchorages = tuple(
            sorted(
                kept + calculator.summaries,
                key=lambda summary: (summary.layer_index, summary.side == "right"),
            )
        )

    def get_horizontal_spacing(self, bar_diameter: float) -> float:
        """
        The minimum horizontal spacing (cm) between bars, according to ABNT NBR 6118 - Section 18.3.2.2
        """
        horizontal_spacing = max(bar_diameter, 2, 1.2 * APP_CONFIG.max_aggregate_size)
        log_property(
            f"Min horizontal spacing for {bar_diameter}mm bars: {horizontal_spacing} cm"
        )
        return horizontal_spacing

    @staticmethod
    def get_vertical_spacing(bar_diameter: float) -> float:
        """
        The minimum vertical spacing (cm) between bars, according to ABNT NBR 6118 - Section 18.3.2.2
        """
        vertical_spacing = max(bar_diameter, 2, 0.5 * APP_CONFIG.max_aggregate_size)
        log_property(
            f"Min vertical spacing for {bar_diameter}mm bars: {vertical_spacing} cm"
        )
        return vertical_spacing

    def get_distance_for_d_calculation(self, d_calculation_label: str) -> float:
        """
        Returns the centroid for the reinforcement relative to itself (cm)
        """
        if not self.is_chosen:
            log_property(
                f"No reinforcement chosen, using default distance for d calculation: {DEFAULT_DISTANCE_FOR_D_CALCULATION} cm"
            )
            return DEFAULT_DISTANCE_FOR_D_CALCULATION
        weighted_centroids = 0.0
        weights = 0.0
        for index, layer in enumerate(self.chosen_bars):
            if layer.bars:
                layer_centroid, layer_weight = (
                    self.get_layer_absolute_centroid_with_weight(index)
                )
                weighted_centroids += layer_centroid * layer_weight
                weights += layer_weight
        distance_for_d_calculation = (
            (weighted_centroids / weights) if weights != 0 else 0.0
        )
        log_property(
            f"Centroid for the reinforcement relative to itself: {distance_for_d_calculation} cm",
            f"Reinforcement {d_calculation_label}",
        )
        return distance_for_d_calculation

    def _update_layers_y_centroids(self) -> None:
        """
        Updates the y_centroid_position for all non-empty layers.
        Must be called before anchorage calculation.
        """
        log_operation("Updating y_centroid_position for all non-empty layers.")
        for index, layer in enumerate(self.chosen_bars):
            if layer.bars:
                self._set_layer_y_centroid_position(index)

    @property
    def area(self) -> float:
        """
        Returns the total area of the chosen reinforcement (cm²)
        """
        return sum(layer.area for layer in self.chosen_bars)

    def effective_covering(self) -> float:
        """Return the covering up to the chosen bars.

        Returns:
            Effective covering (cm).
        """
        if self.stacked_on is not None:
            return self.stacked_on.effective_covering()
        covering = RectangularBeam.nominal_covering  # cm
        first_layer_bars = self.chosen_bars[0].bars
        if not first_layer_bars:
            return covering
        return max(bar.effective_covering(covering) for bar in first_layer_bars)

    def _stirrup_diameter(self) -> float:
        """Return the chosen stirrup diameter, or the default while none is chosen (cm)."""
        if self.stirrup_diameter is not None:
            return self.stirrup_diameter
        return DEFAULT_STIRRUP_DIAMETER_FOR_D_CALCULATION

    def _face_offset(self) -> float:
        """Return the distance (cm) from the section face to the stirrup's inner face."""
        return self.effective_covering() + self._stirrup_diameter()

    def face_extent(self) -> float:
        """Return the distance from the section face to the inner edge of the bars on it (cm)

        Without chosen bars, the face still gets construction bars in the stirrup corners, with the stirrup's diameter (see ``add_construction_bars``).
        """
        if not any(layer.bars for layer in self.chosen_bars):
            return self._face_offset() + self._stirrup_diameter()
        return self._face_offset() + self.stack_top()[0]

    @property
    def stirrup_inner_width(self) -> float:
        """Return the width between the stirrup's inner faces (cm)"""
        return self.beam.width - 2 * self._face_offset()

    def get_layer_absolute_centroid_with_weight(
        self, layer_index: int
    ) -> tuple[float, float]:
        """
        Returns the centroid of a layer (cm) measured from the stirrup's inner face at the reinforced side, considering the spacing and previous layers.
        """
        self._validate_layer_index(layer_index)

        layer_centroid, layer_weight = self.get_layer_relative_centroid_with_weight(
            layer_index
        )
        layer_centroid_from_closest_edge = layer_centroid + self._layer_offset(
            layer_index
        )
        log_property(
            f"Absolute Centroid for Layer {layer_index}: {layer_centroid_from_closest_edge:.2f} cm from the {'bottom' if self.is_bottom_reinforcement else 'top'} stirrup's inner face"
        )
        return layer_centroid_from_closest_edge, layer_weight

    def _layer_offset(self, layer_index: int) -> float:
        """Return the distance from the stirrup's inner face to the near edge of a layer (cm)

        Each previous layer adds its largest bar diameter and the minimum vertical spacing for that diameter. A stacked reinforcement starts after its base's last layer, with the minimum vertical spacing for the larger of the two diameters across the gap.

        References:
            ABNT NBR 6118:2026 — Section 18.3.2.2
        """
        offset = 0.0
        if self.stacked_on is not None:
            base_edge, base_diameter = self.stacked_on.stack_top()  # cm
            first_diameter = (
                max(b.diameter_mm for b in self.chosen_bars[0].bars) / 10
            )  # cm
            offset = base_edge + self.get_vertical_spacing(
                max(base_diameter, first_diameter)
            )
        for i in range(layer_index):
            max_dia = max(b.diameter_mm for b in self.chosen_bars[i].bars) / 10
            offset += self.get_vertical_spacing(max_dia) + max_dia
        return offset

    def stack_top(self) -> tuple[float, float]:
        """Return the far edge of the last non-empty layer and its largest bar diameter

        Returns:
            Distance from the stirrup's inner face to the far edge of the last
            non-empty layer (cm), and that layer's largest bar diameter (cm).

        Raises:
            EnginePreconditionError: If no layer has bars.
        """
        used = [i for i, layer in enumerate(self.chosen_bars) if layer.bars]
        if not used:
            raise EnginePreconditionError("No bars chosen to stack on.")
        last = used[-1]
        diameter = max(b.diameter_mm for b in self.chosen_bars[last].bars) / 10  # cm
        return self._layer_offset(last) + diameter, diameter

    def _clamps_stack_height(self, diameter_mm: float, quantity: int) -> float:
        """Return the height from the stirrup's inner face to the far edge of the clamp rows (cm)

        Each clamp is a row with its two legs at the stirrup's inner corners. The rows are stacked after the last non-empty layer, with the minimum vertical spacing between rows; the spacing to the last layer uses the larger of the two diameters.

        Args:
            diameter_mm: Clamp bar diameter φ (mm).
            quantity: Number of clamps, one row each.

        References:
            ABNT NBR 6118:2026 — Section 18.3.2.2
        """
        last_index = max(i for i, layer in enumerate(self.chosen_bars) if layer.bars)
        last_diameter = (
            max(b.diameter_mm for b in self.chosen_bars[last_index].bars) / 10
        )  # cm
        diameter = diameter_mm / 10  # cm
        height = self._layer_offset(last_index) + last_diameter  # cm
        height += self.get_vertical_spacing(max(last_diameter, diameter)) + diameter
        height += (quantity - 1) * (self.get_vertical_spacing(diameter) + diameter)
        return height

    def clamps_fit(self, diameter_mm: float, quantity: int) -> bool:
        """Check whether the clamps fit in the reinforced half of the section

        The clamp rows, stacked after the layers, must stay between the stirrup's inner face at the reinforced side and the section's mid-height.

        Args:
            diameter_mm: Clamp bar diameter φ (mm).
            quantity: Number of clamps, one row each.
        """
        height = self._clamps_stack_height(diameter_mm, quantity)  # cm
        room = self.beam.height / 2 - self._face_offset()  # cm
        does_fit = height <= room
        log_property(
            f"Clamps {quantity}x{diameter_mm:g}mm: stack height = {height:.2f} cm, "
            f"room up to mid-height = {room:.2f} cm, Fits: {'Yes' if does_fit else 'No'}"
        )
        return does_fit

    def _set_layer_y_centroid_position(self, layer_index: int) -> None:
        """
        Sets the y_centroid_position (cm from the bottom face of the section) for a specific layer, adding the cover and stirrup to the layer's centroid from the stirrup's inner face.
        """
        layer_centroid_from_stirrup, _ = self.get_layer_absolute_centroid_with_weight(
            layer_index
        )
        layer_centroid_from_face = self._face_offset() + layer_centroid_from_stirrup

        position_from_bottom_edge = (
            layer_centroid_from_face
            if self.is_bottom_reinforcement
            else self.beam.height - layer_centroid_from_face
        )

        log_property(
            f"Setting y_centroid_position for Layer {layer_index}: {position_from_bottom_edge:.2f} cm from bottom edge"
        )
        self.chosen_bars[layer_index].y_centroid_position = position_from_bottom_edge

    def _validate_layer_index(self, layer_index: int) -> None:
        """
        Validates that the layer index is within the valid range.
        Raises EnginePreconditionError if the index is out of bounds.
        """
        if not 0 <= layer_index < len(self.chosen_bars):
            raise EnginePreconditionError(
                f"Layer index must be between 0 and {len(self.chosen_bars) - 1}."
            )

    def get_layer_relative_centroid_with_weight(
        self, layer_index: int
    ) -> tuple[float, float]:
        """
        Calculates the average of the vertical centroid (cm) for each bar of the layer, weighted by the area of each bar.
        It does not take into account which layer is it, therefore, it is the distance from the edge of the layer to the centroid of the bars in that layer, not from the edge of the section.
        """
        self._validate_layer_index(layer_index)

        bars = self.chosen_bars[layer_index].bars
        weighted_centroids = 0.0
        weights = 0.0
        for bar in bars:
            area = bar.area_cm2
            bar_diameter_cm = bar.diameter_mm / 10
            weighted_centroids += area * (bar_diameter_cm / 2)
            weights += area
        return (weighted_centroids / weights, weights) if weights != 0 else (0.0, 0.0)

    def distribute_bars_in_layers(self, optimal_reinforcement: list[Rebar]) -> None:
        """
        Gets the optimal reinforcement combination chosen and distributes the bars in layers, ensuring that the spacing and constructability requirements are met.
        """
        if self.check_for_enough_space(optimal_reinforcement):
            self.chosen_bars[0].bars = list(optimal_reinforcement)
            for layer in self.chosen_bars[1:]:
                layer.bars = []
            log_operation(
                f"All bars fit in a single layer. Total bars: {len(optimal_reinforcement)}"
            )
            return

        current_layer = 0
        for rebar, count in self._sort_bars_by_diameter(optimal_reinforcement):
            current_layer = self._add_rebar_to_layers(rebar, count, current_layer)

    def _sort_bars_by_diameter(self, bars: list[Rebar]) -> list[tuple[Rebar, int]]:
        counts = Counter(bars)
        return sorted(counts.items(), key=lambda x: x[0].diameter_mm, reverse=True)

    def _add_rebar_to_layers(self, rebar: Rebar, count: int, current_layer: int) -> int:
        """Place bars first-fit, advancing a layer only when the next bar doesn't fit

        Bars of one diameter share a single Rebar instance within a layer. A diameter that continues into the next layer gets a copy there, because the anchorage lengths and hooks are set on the bars layer by layer.

        Args:
            rebar: Bar to place, repeated count times.
            count: Number of bars to place.
            current_layer: Index of the layer to start filling.

        Returns:
            Index of the layer the last bar went into, where the next (smaller)
            diameter group continues.

        Raises:
            MaxLayersExceededError: If the bars need more than the maximum number of layers.
        """
        while count > 0:
            if current_layer >= len(self.chosen_bars):
                self.clear_chosen_bars()
                raise MaxLayersExceededError(
                    "Cannot distribute bars within the maximum number of layers.",
                    max_layers=len(self.chosen_bars),
                )
            if self.check_for_enough_space(
                self.chosen_bars[current_layer].bars + [rebar]
            ):
                self.chosen_bars[current_layer].bars.append(rebar)
                count -= 1
            else:
                current_layer += 1
                rebar = copy(rebar)  # the next layer owns its bars' lengths

        log_property(
            f"Distributed {rebar.diameter_mm}mm bars up to layer {current_layer} ({current_layer + 1} layers in use)."
        )
        return current_layer

    def arrange_bars(self) -> None:
        """
        Arranges the bars for every layer to maintain symmetry and proper spacing, making it easier to build.
        This function should be called after distributing bars in layers, to ensure that the arrangement is optimized
        """
        log_operation("Arranging bars in layers")
        for layer in self.chosen_bars:
            self.arrange_bars_in_layer(layer)
            log_property(
                f"Layer {layer.layer_index} arranged as {layer.get_bar_diameters_for_print()}."
            )

    def arrange_bars_in_layer(self, layer: Layer) -> None:
        """Reorder the layer's bars in place so the row is easy to build

        Rules, in priority order: the row is symmetric (a palindrome by diameter), and the largest diameters sit on the outside. Bars of each diameter are paired, largest first, and mirrored from the edges inwards; an odd bar is placed in the center. When more than one diameter has an odd count, perfect symmetry is impossible and the unpaired bars fill the middle, largest alternating outer-left and outer-right.
        """
        if len(layer.bars) <= 1:
            return

        bars_by_diameter: dict[float, list[Rebar]] = {}
        for bar in layer.bars:
            bars_by_diameter.setdefault(bar.diameter_mm, []).append(bar)

        left: list[Rebar] = []
        right: list[Rebar] = []
        leftovers: list[Rebar] = []
        for diameter in sorted(bars_by_diameter, reverse=True):
            bars = bars_by_diameter[diameter]
            pairs_count = len(bars) // 2
            left.extend(bars[:pairs_count])
            right.extend(bars[pairs_count : 2 * pairs_count])
            if len(bars) % 2 == 1:
                leftovers.append(bars[-1])

        middle_left = leftovers[0::2]
        middle_right = leftovers[1::2]
        layer.bars = (
            left + middle_left + list(reversed(middle_right)) + list(reversed(right))
        )

    def clear_chosen_bars(self) -> None:
        """
        Clears the chosen bars, resetting the state for a new attempt at distribution.
        """
        log_operation("Clearing chosen bars and resetting layers.")
        self.chosen_bars = self._build_empty_layers()

    def check_for_enough_space(self, optimal_reinforcement: list[Rebar]) -> bool:
        """
        Checks if there is enough space for a reinforcement choice within a layer.
        """
        if not optimal_reinforcement:
            return True

        diameters_in_cm = [bar.diameter_mm / 10 for bar in optimal_reinforcement]
        max_diameter = max(diameters_in_cm)
        required_spacing = self.get_horizontal_spacing(max_diameter)

        total_bar_width = sum(diameters_in_cm)
        total_spacing = (len(optimal_reinforcement) - 1) * required_spacing
        total_width_needed = total_bar_width + total_spacing

        max_effective_covering = max(
            bar.effective_covering(RectangularBeam.nominal_covering)
            for bar in optimal_reinforcement
        )
        available_width = self.beam.width - 2 * (
            max_effective_covering + self._stirrup_diameter()
        )
        is_there_enough_space = total_width_needed <= available_width
        log_property(
            f"Checking space for {len(optimal_reinforcement)} bars: "
            f"Total width needed = {total_width_needed:.2f} cm, "
            f"Available width = {available_width:.2f} cm, "
            f"Enough space: {'Yes' if is_there_enough_space else 'No'}"
        )
        return is_there_enough_space


def _side_length(layer: Layer, left: bool) -> float:
    """Return the longest bar length of a layer on one side of the section (cm)"""
    return max(bar.left_length if left else bar.right_length for bar in layer.bars)
