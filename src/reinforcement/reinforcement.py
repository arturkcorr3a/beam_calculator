from typing import List, Tuple
from math import pi
from src.properties.steel import Steel

class Reinforcement:
    def __init__(self, required_area: float, steel: Steel):
        self.required_area = required_area
        self.steel = steel
        self.chosen_bars: Tuple[List[int],List[int],List[int]] = ([], [], []) # list of chosen rebar sizes (e.g., [16, 16, 12]) per layer
        self.total_area = 0.0 # total area of the chosen rebars
        self.choose()

    def choose(self) -> None:
        # TODO implement a method to choose the rebar sizes based on the required area and available sizes
        # IMPLEMENT
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