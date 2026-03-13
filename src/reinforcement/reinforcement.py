from typing import List, Tuple
from math import ceil
from src.beam.rectangular_beam import RectangularBeam
from collections import Counter

MAX_AGGREGATE_SIZE = 2.5 # CONFIRM valor e referência disso, para colocar no #PAPER
MAX_BAR_TYPES = 3
MAX_LAYERS = 3

# TODO guardar várias opções de reforço escolhido
class Reinforcement:
    """
    Defines the longitudinal reinforcement, by layer.
    """
    def __init__(self, beam: RectangularBeam):
        self.beam = beam
        self.steel = beam.steel
        self.chosen_bars: List[List[float]] = [[] for _ in range(MAX_LAYERS)] # list of chosen rebar sizes per layer
        self.is_chosen = False

    def set_required_area(self, required_area: float) -> None:
        self.required_area = required_area
        self.choose()

    def choose(self) -> None:
        # FIXME quando tiver várias opções, fazer while com try-catch dentro para pegar os erros
        if self.required_area is None:
            raise ValueError("Required area must be set before choosing reinforcement.")
        optimal_reinforcement = self.choose_optimal_reinforcement()
        self.distribute_bars_in_layers(optimal_reinforcement)
        # TODO fazer uma outra função que organiza as barras da camada, mantendo simetrico
        self.is_chosen = True

    def calculate_necessary_bars(self, diameter: float) -> int:
        return ceil(self.required_area / self.steel.get_area(diameter))

    def get_horizontal_spacing(self, bar_diameter: float) -> float:
        """
        The minimum horizontal spacing (cm) between bars, according to ABNT NBR 6118 - Section 18.3.2.2
        """
        return max(bar_diameter, 2, 1.2*MAX_AGGREGATE_SIZE)
    
    def get_vertical_spacing(self, bar_diameter: float) -> float:
        """
        The minimum vertical spacing (cm) between bars, according to ABNT NBR 6118 - Section 18.3.2.2
        """
        return max(bar_diameter, 2, 0.5*MAX_AGGREGATE_SIZE)

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
                return (layer_centroid + self.get_vertical_spacing + max(self.chosen_bars[0])), layer_weigth
            case 2:
                return (layer_centroid + 2 * self.get_vertical_spacing + max(self.chosen_bars[0]) + max(self.chosen_bars[1])), layer_weigth
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

    # REFACTOR tirar essa função para outra classe, por organização?
    def choose_optimal_reinforcement(self, max_bar_types: int = MAX_BAR_TYPES, min_bars: int = 2) -> List[float]:
        # PAPER achar uma referência disso para colocar no trabalho? (do problema da moeda)
        """
        Optimizes the reinforcement selection using dynamic programming (based on the coin change problem).
        Finds the combination with minimum number of bars that meets the required area,
        limiting the number of different bar types for practical construction.
        
        Args:
            max_bar_types: Maximum number of different bar diameters allowed (default: 2)
            min_bars: Minimum number of bars required (default: 2)
            
        Returns:
            List of chosen bar diameters
        """
        # Support functions
        def initialize_dp_table() -> Tuple[List, int, int]:
            """Initialize the dynamic programming table for reinforcement optimization."""
            target_area_int = int(self.required_area * 100)
            max_bar_area_int = int(max(self.steel.get_area(d) for d in self.steel.available_sizes) * 100)
            limit = target_area_int + max_bar_area_int
            
            dp = [None] * (limit + 1)
            dp[0] = []
            return dp, target_area_int, limit

        def is_valid_combination(combination: List[float], max_bar_types: int, min_bars: int) -> bool:
            """Check if a bar combination meets the diversity and minimum requirements."""
            has_enough_bars = len(combination) >= min_bars
            has_allowable_bar_types = len(set(combination)) <= max_bar_types
            return has_enough_bars and has_allowable_bar_types

        def should_update_dp(dp: List, index: int, new_combination: List[float]) -> bool:
            """Determine if the new combination is better than the existing one."""
            # TODO adicionar preferência para combinações que não usem diâmetro de 40 (é muito pouco usual)
            # PAPER comentar isso no trabalho
            if dp[index] is None:
             return True 
            
            # Prefer combinations with fewer bars
            if len(new_combination) < len(dp[index]):
              return True
            
            # For same number of bars, prefer symmetrical arrangements
            return Reinforcement.is_symmetrical(new_combination)

        def find_optimal_solution(dp: List, target_area_int: int, limit: int) -> List[float]:
            """Find the first valid result that meets or exceeds the required area."""
            for i in range(target_area_int, limit + 1):
                if dp[i] is not None and Reinforcement.is_symmetrical(dp[i]):
                    return sorted(dp[i], reverse=True)
            raise ValueError("No valid reinforcement combination found within the limit.")
        
        # Actual function logic
        dp, target_area_int, limit = initialize_dp_table()
        
        for i in range(limit):
            if dp[i] is not None:
                for diameter in self.steel.available_sizes:
                    area_int = int(self.steel.get_area(diameter) * 100)
                    new_index = i + area_int
                    
                    if new_index <= limit:
                        new_combination = dp[i] + [diameter]
                        
                        if is_valid_combination(new_combination, max_bar_types, min_bars):
                            if should_update_dp(dp, new_index, new_combination):
                                dp[new_index] = new_combination
        
        return find_optimal_solution(dp, target_area_int, limit)
    
    def distribute_bars_in_layers(self, optimal_reinforcement: List[float]) -> None:
        # REFACTOR organizar melhor esse código com funções auxiliares
        if self.check_for_enough_space(optimal_reinforcement):
            self.chosen_bars = (optimal_reinforcement, [], [])
            return None

        diameters_count = Counter(optimal_reinforcement)
        diameters_sorted = sorted(diameters_count.items(), key=lambda x: x[0], reverse=True) # sort by diameter, larger first
        current_layer = 0
        for diameter, count in diameters_sorted:
             # check if all bars of this diameter can fit in one layer
            if self.check_for_enough_space(self.chosen_bars[current_layer] + [diameter] * count):
                self.chosen_bars[current_layer].extend([diameter] * count)
                current_layer += 1
            else:
                while count > 0:
                    if current_layer >= MAX_LAYERS:
                        raise ValueError("Cannot distribute bars within the maximum number of layers.")
                    if self.check_for_enough_space(self.chosen_bars[current_layer] + [diameter]): 
                        self.chosen_bars[current_layer].append(diameter)
                        count -= 1
                    else:
                        current_layer += 1

    def check_for_enough_space(self, optimal_reinforcement: List[float]) -> bool:
        max_diameter = max(optimal_reinforcement)
        required_spacing = self.get_horizontal_spacing(max_diameter)

        total_bar_width = sum(optimal_reinforcement)
        total_spacing = (len(optimal_reinforcement) - 1) * required_spacing
        total_width_needed = total_bar_width + total_spacing

        available_width = self.beam.width - 2 * self.beam.nominal_covering
        return total_width_needed <= available_width

    # REFACTOR se é estático e eu criar outra classe pra escolher, esse pode ir junto
    # TODO reaproveitar isso na função de organizar as barras na camada, para manter simétrico
    @staticmethod
    def is_symmetrical(combination: List[float]) -> bool:
        """Check if a bar combination can be arranged symmetrically."""
        if len(combination) % 2 == 0:
            # Even number of bars - check if counts are even for each diameter
            counts = Counter(combination)
            return all(count % 2 == 0 for count in counts.values())
        # Odd number of bars - one diameter can have odd count (will be centered)
        counts = Counter(combination)
        odd_counts = sum(1 for count in counts.values() if count % 2 != 0)
        return odd_counts <= 1