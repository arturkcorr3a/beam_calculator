from typing import List, Tuple
from math import pi
from src.properties.steel import Steel

MAX_AGGREGATE_SIZE = 2.5 # CONFIRM value for this, its a random value for now, but it should be based on a solid reference

class Reinforcement:
    """
    Defines the longitudinal reinforcement, by layer.
    """
    def __init__(self, steel: Steel):
        self.steel = steel
        self.chosen_bars: Tuple[List[float],List[float],List[float]] = ([], [], []) # list of chosen rebar sizes per layer
        self.is_chosen = False
        self.choose()

    def set_required_area(self, required_area: float) -> None:
        self.required_area = required_area
        self.choose()

    def choose(self) -> None:
        # IMPLEMENT
        self.is_chosen = True
        pass

    @property
    def horizontal_spacing(self) -> float:
        """
        The minimum horizontal spacing (cm) between bars, according to ABNT NBR 6118 - Section 18.3.2.2
        """
        return max(self.max_bar, 2, 1.2*MAX_AGGREGATE_SIZE)

    @property
    def vertical_spacing(self) -> float:
        """
        The minimum vertical spacing (cm) between bars, according to ABNT NBR 6118 - Section 18.3.2.2
        """
        return max(self.max_bar, 2, 0.5*MAX_AGGREGATE_SIZE)

    @property
    def max_bar(self) -> float:
        """Returns the maximum diameter of the chosen bars (cm)"""
        return max([max(layer) for layer in self.chosen_bars if layer]) if any(self.chosen_bars) / 10 else 0.0

    @property
    def total_area(self) -> float:
        """
        Returns the total area of the chosen reinforcement (cm²)
        """
        total_area = 0
        for layer in self.chosen_bars:
            for bar in layer:
                total_area += self.steel.get_area(bar)
        return total_area

    def get_distance_for_d_calculation(self) -> float:
        """
        Returns the centroid for the reinforcement relative to itself (cm)
        """
        weighted_centroids = 0
        weights = 0
        for index, layer in enumerate(self.chosen_bars):
            if layer:
                layer_centroid, layer_weight = self.get_layer_absolute_centroid_with_weight(index)
                weighted_centroids += layer_centroid * layer_weight
                weights += layer_weight
        return (weighted_centroids / weights) / 10 if weights != 0 else 0

    def get_layer_absolute_centroid_with_weight(self, layer: int) -> Tuple[float, float]:
        """
        Returns the absolute centroid for each layer, considering the spacing and previous layers
        """
        layer_centroid, layer_weigth = self.get_layer_relative_centroid_with_weight(layer)
        match layer:
            case 0:
                return layer_centroid, layer_weigth
            case 1:
                return (layer_centroid + self.vertical_spacing + max(self.chosen_bars[0])), layer_weigth
            case 2:
                return (layer_centroid + 2 * self.vertical_spacing + max(self.chosen_bars[0]) + max(self.chosen_bars[1])), layer_weigth
            case _:
                raise ValueError("Layer index must be between 0 and 2.")

    def get_layer_relative_centroid_with_weight(self, layer: int) -> Tuple[float, float]:
        """
        Calculates the average of the vertical centroid (mm) for each bar of the layer, weighted by the area of each bar.
        It does not take into account which layer is it, therefore, it is the distance from the edge of the layer to the centroid of the bars in that layer, not from the edge of the section.
        """
        if not (0 <= layer <= 2):
            raise ValueError("Layer index must be between 0 and 2.")
        layer = self.chosen_bars[layer]
        weighted_centroids = 0
        weights = 0
        for bar in layer:
            weighted_centroids += self.steel.get_area(bar) * (bar / 2)
            weights += self.steel.get_area(bar)
        return (weighted_centroids / weights, weights) if weights != 0 else (0,0)
            