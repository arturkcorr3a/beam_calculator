from collections import Counter

from src.config import APP_CONFIG
from src.logger import log_element
from src.reinforcement.rebar_chooser import RebarChooser
from src.structural_elements.rebar import Rebar
from src.structural_elements.rectangular_beam import RectangularBeam

# TODO find a good reference for this initial guess, to have a basis in the work and know how to justify it
DEFAULT_DISTANCE_FOR_D_CALCULATION = 1.0  # cm, default 1 layer with 20 mm bars, for calculating effective depth d when no reinforcement is chosen


class Reinforcement:
    """
    Defines the longitudinal reinforcement, by layer.
    """

    required_area: float | None = None  # cm², to be calculated

    def __init__(self, beam: RectangularBeam):
        self.beam = beam
        self.steel = beam.steel
        self.chosen_bars: list[list[Rebar]] = [
            [] for _ in range(APP_CONFIG.max_layers)
        ]  # list of chosen rebar sizes per layer
        self.is_chosen = False
        self.rebar_choice_options = []

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
                break
            except ValueError:
                continue
        if len(self.chosen_bars[0]) == 0:
            raise ValueError("No valid reinforcement combination found.")
        self.is_chosen = True
        all_bars = [bar for layer in self.chosen_bars for bar in layer]
        counter = Counter(int(b.diameter_mm) for b in all_bars)
        bar_desc = ", ".join(
            f"{count}x{d}mm" for d, count in sorted(counter.items(), reverse=True)
        )
        log_element(f"required {self.required_area:.2f} cm2: {bar_desc}")

    def get_horizontal_spacing(self, bar_diameter: float) -> float:
        """
        The minimum horizontal spacing (cm) between bars, according to ABNT NBR 6118 - Section 18.3.2.2
        """
        return max(bar_diameter, 2, 1.2 * APP_CONFIG.max_aggregate_size)

    def get_vertical_spacing(self, bar_diameter: float) -> float:
        """
        The minimum vertical spacing (cm) between bars, according to ABNT NBR 6118 - Section 18.3.2.2
        """
        return max(bar_diameter, 2, 0.5 * APP_CONFIG.max_aggregate_size)

    def get_distance_for_d_calculation(self) -> float:
        """
        Returns the centroid for the reinforcement relative to itself (cm)
        """
        if not self.is_chosen:
            return DEFAULT_DISTANCE_FOR_D_CALCULATION
        weighted_centroids = 0
        weights = 0
        for index, layer in enumerate(self.chosen_bars):
            if layer:
                layer_centroid, layer_weight = (
                    self.get_layer_absolute_centroid_with_weight(index)
                )
                weighted_centroids += layer_centroid * layer_weight
                weights += layer_weight
        return (weighted_centroids / weights) / 10 if weights != 0 else 0

    @property
    def area(self) -> float:
        """
        Returns the total area of the chosen reinforcement (cm²)
        """
        return sum(bar.area_cm2 for layer in self.chosen_bars for bar in layer)

    def get_layer_absolute_centroid_with_weight(
        self, layer: int
    ) -> tuple[float, float]:
        """
        Returns the absolute centroid for each layer, considering the spacing and previous layers
        """
        layer_centroid, layer_weight = self.get_layer_relative_centroid_with_weight(
            layer
        )
        match layer:
            case 0:
                return layer_centroid, layer_weight
            case 1:
                max_dia_0 = max(b.diameter_mm for b in self.chosen_bars[0]) / 10
                return (
                    layer_centroid + self.get_vertical_spacing(max_dia_0) + max_dia_0
                ), layer_weight
            case 2:
                max_dia_0 = max(b.diameter_mm for b in self.chosen_bars[0]) / 10
                max_dia_1 = max(b.diameter_mm for b in self.chosen_bars[1]) / 10
                return (
                    layer_centroid
                    + 2 * self.get_vertical_spacing(max_dia_0)
                    + max_dia_0
                    + max_dia_1
                ), layer_weight
            case _:
                raise ValueError("Layer index must be between 0 and 2.")

    def get_layer_relative_centroid_with_weight(
        self, layer: int
    ) -> tuple[float, float]:
        """
        Calculates the average of the vertical centroid (mm) for each bar of the layer, weighted by the area of each bar.
        It does not take into account which layer is it, therefore, it is the distance from the edge of the layer to the centroid of the bars in that layer, not from the edge of the section.
        """
        if not (0 <= layer <= 2):
            raise ValueError("Layer index must be between 0 and 2.")
        bars = self.chosen_bars[layer]
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
            self.chosen_bars = [list(optimal_reinforcement), [], []]
            return

        current_layer = 0
        for rebar, count in self._sort_bars_by_diameter(optimal_reinforcement):
            current_layer = self._add_rebar_to_layers(rebar, count, current_layer)

    def _sort_bars_by_diameter(self, bars: list[Rebar]) -> list[tuple[Rebar, int]]:
        counts = Counter(bars)
        return sorted(counts.items(), key=lambda x: x[0].diameter_mm, reverse=True)

    def _add_rebar_to_layers(self, rebar: Rebar, count: int, current_layer: int) -> int:
        bars_to_add = [rebar] * count
        if self.check_for_enough_space(self.chosen_bars[current_layer] + bars_to_add):
            self.chosen_bars[current_layer].extend(bars_to_add)
            return current_layer + 1

        while count > 0:
            if current_layer >= APP_CONFIG.max_layers:
                self.clear_chosen_bars()
                raise ValueError(
                    "Cannot distribute bars within the maximum number of layers."
                )
            if self.check_for_enough_space(self.chosen_bars[current_layer] + [rebar]):
                self.chosen_bars[current_layer].append(rebar)
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

    def arrange_bars_in_layer(self, layer: list[Rebar]) -> None:
        """
        Arranges the bars within a specific layer to maintain symmetry and proper spacing.
        """
        # IMPLEMENT arrange bars to make it easier to build - this can be done afterwards, when it is time to create the drawings.

    def clear_chosen_bars(self) -> None:
        """
        Clears the chosen bars, resetting the state for a new attempt at distribution.
        """
        self.chosen_bars = [[] for _ in range(APP_CONFIG.max_layers)]

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
