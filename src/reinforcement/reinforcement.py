from collections import Counter
from typing import cast

from src.calculators.anchorage_calculator import AnchorageCalculator
from src.config import APP_CONFIG
from src.logger import (
    log_element,
    log_iteration,
    log_operation,
    log_property,
    logger_label,
)
from src.reinforcement.layer import Layer
from src.reinforcement.rebar_chooser import RebarChooser
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
    ):
        self.beam = beam
        self.steel = beam.steel
        self.chosen_bars: tuple[Layer, ...] = self._build_empty_layers()
        self.is_chosen = False
        self.rebar_choice_options: tuple[tuple[Rebar, ...], ...] = ()
        self.is_bottom_reinforcement = is_bottom_reinforcement
        self.center_position = center_position
        self.moment_zeros = moment_zeros  # cm, positions where M = 0
        self.moment_shift: float | None = None  # cm, a_l
        self.stirrup_diameter: float | None = None  # cm
        self.effective_depth: float | None = None  # cm, d, used by clamps
        self.design_shear: float | None = None  # kN, V_d, used by clamps
        self.id = id

    def _build_empty_layers(self) -> tuple[Layer, ...]:
        """Builds a tuple of empty layers for the reinforcement, based on the maximum number of layers defined in the configuration."""
        return tuple(
            Layer([], i) for i in range(APP_CONFIG.max_layers)
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
            ValueError: If the required area or moment shift is not set, if
                clamps are needed but the effective depth or design shear is not
                set, or if no option can be laid out and anchored, even with
                clamps.
        """
        log_operation(
            f"Choosing reinforcement for required area: {self.required_area:.2f} cm²"
        )
        if self.required_area is None:
            raise ValueError("Required area must be set before choosing reinforcement.")
        if self.moment_shift is None:
            raise ValueError("Moment shift must be set before choosing reinforcement.")

        rebar_chooser = RebarChooser(self.steel, self.required_area)
        self.rebar_choice_options = rebar_chooser.ranked_solutions

        best_layers = self._select_best_layers(allow_clamp=False)
        if best_layers is None:
            log_operation(
                "No combination anchors without clamps; retrying allowing clamps."
            )
            if self.effective_depth is None or self.design_shear is None:
                self.clear_chosen_bars()
                raise ValueError(
                    "Effective depth and design shear must be set before allowing clamps."
                )
            best_layers = self._select_best_layers(allow_clamp=True)
        if best_layers is None:
            self.clear_chosen_bars()
            raise ValueError("No valid reinforcement combination found.")

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

        Args:
            allow_clamp: Whether clamps may complete the anchorage at the
                extremity supports.

        Returns:
            The laid-out layers of the best option, or None if no option fits.
        """
        # Options come sorted by area: the first buildable one sets the band, and within it fewer layers, then fewer bars, win
        best_layers: tuple[Layer, ...] | None = None
        best_key: tuple[int, int, float] | None = None
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

        Bars centered on an end support are anchored only towards the beam interior: at the beam start (x = 0) the left length stays zero, and at the beam end (x = L) the right length stays zero.

        Args:
            allow_clamp: Whether clamps may complete the anchorage at the
                extremity supports.

        Raises:
            ValueError: Propagated from the anchorage calculator if there isn't enough space for anchorage, even after adding hooks (and clamps, when allowed).
        """
        log_operation("Running anchorage calculation for chosen reinforcement layers.")
        moment_shift = cast(float, self.moment_shift)
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

            if self._is_at_beam_start:
                is_left = True
                layer.set_hooks(is_left, True)
                layer.set_anchorage_length(0.0, is_left)
            else:
                left_available_space = (
                    self.center_position - RectangularBeam.nominal_covering
                )  # cm
                anchorage_calculator.run(
                    left_available_space, left=True, allow_clamp=allow_clamp
                )

            if self._is_at_beam_end:
                is_left = False
                layer.set_hooks(is_left, True)
                layer.set_anchorage_length(0.0, is_left)
            else:
                right_available_space = (
                    self.beam.length - RectangularBeam.nominal_covering
                ) - self.center_position  # cm
                anchorage_calculator.run(
                    right_available_space, left=False, allow_clamp=allow_clamp
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

        offset = 0.0
        for i in range(layer_index):
            max_dia = max(b.diameter_mm for b in self.chosen_bars[i].bars) / 10
            offset += self.get_vertical_spacing(max_dia) + max_dia

        layer_centroid_from_closest_edge = layer_centroid + offset
        log_property(
            f"Absolute Centroid for Layer {layer_index}: {layer_centroid_from_closest_edge:.2f} cm from the {'bottom' if self.is_bottom_reinforcement else 'top'} stirrup's inner face"
        )
        return layer_centroid_from_closest_edge, layer_weight

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
        Raises a ValueError if the index is out of bounds.
        """
        if not 0 <= layer_index < len(self.chosen_bars):
            raise ValueError(
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

        Args:
            rebar: Bar to place, repeated count times.
            count: Number of bars to place.
            current_layer: Index of the layer to start filling.

        Returns:
            Index of the layer the last bar went into, where the next (smaller)
            diameter group continues.

        Raises:
            ValueError: If the bars need more than the maximum number of layers.
        """
        while count > 0:
            if current_layer >= APP_CONFIG.max_layers:
                self.clear_chosen_bars()
                raise ValueError(
                    "Cannot distribute bars within the maximum number of layers."
                )
            if self.check_for_enough_space(
                self.chosen_bars[current_layer].bars + [rebar]
            ):
                self.chosen_bars[current_layer].bars.append(rebar)
                count -= 1
            else:
                current_layer += 1

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
