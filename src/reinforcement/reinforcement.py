from collections import Counter

from src.calculators.anchorage_calculator import AnchorageCalculator
from src.calculators.stirrup_calculator import StirrupCalculator
from src.config import APP_CONFIG
from src.logger import log_element, log_property, logger_label
from src.reinforcement.layer import Layer
from src.reinforcement.rebar_chooser import RebarChooser
from src.structural_elements.rebar import Rebar
from src.structural_elements.rectangular_beam import RectangularBeam

DEFAULT_DISTANCE_FOR_D_CALCULATION = 1.0  # cm, default 1 layer with 20 mm bars, for calculating effective depth d when no reinforcement is chosen

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
        stirrup_calculator: StirrupCalculator,
        id: str = "",
    ):
        self.beam = beam
        self.steel = beam.steel
        self.chosen_bars: tuple[Layer, ...] = self._build_empty_layers()
        self.is_chosen = False
        self.rebar_choice_options = []
        self.is_bottom_reinforcement = is_bottom_reinforcement
        self.center_position = center_position
        self.stirrup_calculator = stirrup_calculator
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
        if self.required_area is None:
            raise ValueError("Required area must be set before choosing reinforcement.")

        rebar_chooser = RebarChooser(self.steel, self.required_area)
        self.rebar_choice_options = rebar_chooser.solutions_per_diameter
        for optimal_reinforcement in self.rebar_choice_options.values():
            try:
                self.distribute_bars_in_layers(list(optimal_reinforcement))
                self.arrange_bars()
                self._update_layers_y_centroids()
                self._run_anchorage_calculation()
                break
            except ValueError:
                self.clear_chosen_bars()
                continue
        if len(self.chosen_bars[0].bars) == 0:
            raise ValueError("No valid reinforcement combination found.")

        self.is_chosen = True
        all_bars = [bar for layer in self.chosen_bars for bar in layer.bars]
        counter = Counter(int(b.diameter_mm) for b in all_bars)
        bar_desc = ", ".join(
            f"{count}x{d}mm" for d, count in sorted(counter.items(), reverse=True)
        )
        log_element(f"required {self.required_area:.2f} cm2: {bar_desc}")

    def _run_anchorage_calculation(self) -> None:
        """
        Runs the anchorage calculation for each layer of the chosen reinforcement, setting the necessary lengths for each bar.
        Raises a ValueError if there isn't enough space for anchorage, even after adding hooks.
        """
        for layer_index, layer in enumerate(self.chosen_bars):
            if len(layer.bars) == 0:
                continue
            anchorage_calculator = AnchorageCalculator(
                reinforcement=self,
                stirrup_calculator=self.stirrup_calculator,
                steel=self.steel,
                concrete=self.beam.concrete,
                layer_index=layer_index,
                id = f"{self.id} | Layer {layer_index}"
            )

            left_available_space = (
                self.center_position - RectangularBeam.nominal_covering
            )  # cm
            anchorage_calculator.run(left_available_space, left=True)

            right_available_space = (
                self.beam.length - RectangularBeam.nominal_covering
            ) - self.center_position  # cm
            anchorage_calculator.run(right_available_space, left=False)

    def get_horizontal_spacing(self, bar_diameter: float) -> float:
        """
        The minimum horizontal spacing (cm) between bars, according to ABNT NBR 6118 - Section 18.3.2.2
        """
        return max(bar_diameter, 2, 1.2 * APP_CONFIG.max_aggregate_size)

    @staticmethod
    def get_vertical_spacing(bar_diameter: float) -> float:
        """
        The minimum vertical spacing (cm) between bars, according to ABNT NBR 6118 - Section 18.3.2.2
        """
        return max(bar_diameter, 2, 0.5 * APP_CONFIG.max_aggregate_size)

    def get_distance_for_d_calculation(self) -> float:
        """
        Returns the centroid for the reinforcement relative to itself (cm)
        """
        # TODO add log_property logs here
        if not self.is_chosen:
            return DEFAULT_DISTANCE_FOR_D_CALCULATION
        weighted_centroids = 0
        weights = 0
        for index, layer in enumerate(self.chosen_bars):
            if layer.bars:
                layer_centroid, layer_weight = (
                    self.get_layer_absolute_centroid_with_weight(index)
                )
                weighted_centroids += layer_centroid * layer_weight
                weights += layer_weight
        return (weighted_centroids / weights) if weights != 0 else 0

    def _update_layers_y_centroids(self) -> None:
        """
        Updates the y_centroid_position for all non-empty layers.
        Must be called before anchorage calculation.
        """
        for index, layer in enumerate(self.chosen_bars):
            if layer.bars:
                self._set_layer_y_centroid_position(index)

    @property
    def area(self) -> float:
        """
        Returns the total area of the chosen reinforcement (cm²)
        """
        return sum(layer.area for layer in self.chosen_bars)

    def get_layer_absolute_centroid_with_weight(
        self, layer_index: int
    ) -> tuple[float, float]:
        """
        Returns the absolute centroid for each layer, considering the spacing and previous layers.
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
            f"Absolute Centroid for Layer {layer_index}: {layer_centroid_from_closest_edge:.2f} cm from {'bottom' if self.is_bottom_reinforcement else 'top'} edge"
        )
        return layer_centroid_from_closest_edge, layer_weight

    def _set_layer_y_centroid_position(self, layer_index: int) -> None:
        """
        Sets the y_centroid_position for a specific layer based on the centroids of the bars in that layer and the spacing from previous layers.
        """
        layer_centroid_from_closest_edge, _ = (
            self.get_layer_absolute_centroid_with_weight(layer_index)
        )

        position_from_bottom_edge = (
            layer_centroid_from_closest_edge
            if self.is_bottom_reinforcement
            else self.beam.height - layer_centroid_from_closest_edge
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
        Calculates the average of the vertical centroid (mm) for each bar of the layer, weighted by the area of each bar.
        It does not take into account which layer is it, therefore, it is the distance from the edge of the layer to the centroid of the bars in that layer, not from the edge of the section.
        """
        self._validate_layer_index(layer_index)

        bars = self.chosen_bars[layer_index].bars
        weighted_centroids = 0
        weights = 0
        for bar in bars:
            area = bar.area_cm2
            bar_diameter_cm = bar.diameter_mm / 10
            weighted_centroids += area * (bar_diameter_cm / 2)
            weights += area
        return (weighted_centroids / weights, weights) if weights != 0 else (0, 0)

    def distribute_bars_in_layers(self, optimal_reinforcement: list[Rebar]) -> None:
        """
        Gets the optimal reinforcement combination chosen and distributes the bars in layers, ensuring that the spacing and constructability requirements are met.
        """
        if self.check_for_enough_space(optimal_reinforcement):
            self.chosen_bars[0].bars = list(optimal_reinforcement)
            for layer in self.chosen_bars[1:]:
                layer.bars = []
            return

        current_layer = 0
        for rebar, count in self._sort_bars_by_diameter(optimal_reinforcement):
            current_layer = self._add_rebar_to_layers(rebar, count, current_layer)

    def _sort_bars_by_diameter(self, bars: list[Rebar]) -> list[tuple[Rebar, int]]:
        counts = Counter(bars)
        return sorted(counts.items(), key=lambda x: x[0].diameter_mm, reverse=True)

    def _add_rebar_to_layers(self, rebar: Rebar, count: int, current_layer: int) -> int:
        bars_to_add = [rebar] * count
        if self.check_for_enough_space(
            self.chosen_bars[current_layer].bars + bars_to_add
        ):
            self.chosen_bars[current_layer].bars.extend(bars_to_add)
            return current_layer + 1

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
        return current_layer

    def arrange_bars(self) -> None:
        """
        Arranges the bars for every layer to maintain symmetry and proper spacing, making it easier to build.
        This function should be called after distributing bars in layers, to ensure that the arrangement is optimized
        """
        for layer in self.chosen_bars:
            self.arrange_bars_in_layer(layer)

    def arrange_bars_in_layer(self, layer: Layer) -> None:
        """
        Arranges the bars within a specific layer to maintain symmetry and proper spacing.
        """
        # IMPLEMENT arrange bars to make it easier to build - this can be done afterwards, when it is time to create the drawings.

    def clear_chosen_bars(self) -> None:
        """
        Clears the chosen bars, resetting the state for a new attempt at distribution.
        """
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
        available_width = self.beam.width - 2 * max_effective_covering
        return total_width_needed <= available_width

    @staticmethod
    def is_symmetrical(combination: list[Rebar]) -> bool:
        """Check if a bar combination can be arranged symmetrically."""
        if len(combination) % 2 == 0:
            # Even number of bars - check if counts are even for each diameter
            counts = Counter(combination)
            return all(count % 2 == 0 for count in counts.values())
        # Odd number of bars - one diameter can have odd count (will be centered)
        counts = Counter(combination)
        odd_counts = sum(1 for count in counts.values() if count % 2 != 0)
        return odd_counts <= 1
