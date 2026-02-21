from typing import List, Tuple
from math import pi
from src.properties.steel import Steel

class Reinforcement:
    """
    Defines the longitudinal reinforcement, by layer.
    """
    def __init__(self, required_area: float, steel: Steel):
        self.required_area = required_area
        self.steel = steel
        self.chosen_bars: Tuple[List[float],List[float],List[float]] = ([], [], []) # list of chosen rebar sizes per layer
        self.total_area = 0.0 # total area of the chosen rebars
        self.choose()

    def choose(self) -> None:
        # IMPLEMENT
        pass

    @property
    def horizontal_spacing(self) -> float:
        # IMPLEMENT
        pass

    @property
    def vertical_spacing(self) -> float:
        # IMPLEMENT
        pass

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
            