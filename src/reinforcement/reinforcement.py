# IMPLEMENT class Rebar with necessary information
# IMPLEMENT include required x provided
from dataclasses import dataclass
from typing import List, Optional, Tuple
from math import pi
from src.properties.steel import Steel

# CONFIRM these sizes, they are probably wrong
# FIXME perhaps move this to Steel class
AVAILABLE_REBAR_SIZES = {
    Steel.CA25: [5, 8, 10, 12.5, 16, 20, 25, 32, 40],
    Steel.CA50: [5, 8, 10, 12.5, 16, 20, 25, 32, 40],
    Steel.CA60: [5, 8, 10, 12.5, 16, 20, 25, 32, 40]
}

class Reinforcement:
    def __init__(self, required_area: float, steel: Steel):
        self.required_area = required_area
        self.steel = steel
        self.chosen_bars: Tuple[List[int],List[int],List[int]] = ([], [], []) # list of chosen rebar sizes (e.g., [16, 16, 12]) per layer
        self.total_area = 0.0 # total area of the chosen rebars
        self.choose()

    def choose(self) -> None:
        # TODO implement a method to choose the rebar sizes based on the required area and available sizes
        pass

    def get_distance_for_d_calculation(self) -> float:
        # IMPLEMENT
        pass  

    def get_distance_for_compressed_d_calculation(self) -> float:
        # IMPLEMENT
        pass  

    @staticmethod
    def get_area_for_bar_size(size: int) -> float:
        """        
        :param size: Bar diameter in mm
        :type size: int
        :return: Area of the bar in cm²
        :rtype: float
        """
        return pi * ((size/2)/10)**2