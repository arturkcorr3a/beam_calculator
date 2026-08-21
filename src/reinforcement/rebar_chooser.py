from functools import cached_property
from itertools import combinations
from math import ceil
from typing import Dict, Set, Tuple
from src.elements.rebar import Rebar
from src.config import APP_CONFIG
from src.properties.steel import Steel

class RebarChooser:
    """Select and store rebar solutions for a given steel grade and required area."""
    steel: Steel
    required_area: float
    solutions_per_diameter: Dict[Tuple[float, ...], Tuple[Rebar, ...]]

    def __init__(self, steel: Steel, required_area: float):
        self.steel = steel
        self.required_area = required_area
        self.set_solutions_per_diameter()

    def set_solutions_per_diameter(self) -> None: 
        """Build the cached best solution for each possible bar-diameter combination."""
        solutions = {}
        for combination in self.possible_diameter_combinations:
            solutions[combination] = self.choose_best_combination(combination)
        self.solutions_per_diameter = solutions

    @cached_property
    def possible_diameter_combinations(self) -> Set[Tuple[float,...]]:
        """
        Assemble all possible combinations of rebar sizes that do not exceed the maximum length.

        :param rebar_sizes: List of available rebar sizes (lengths).
        :return: List of valid combinations of rebar sizes.
        """
        possible_combinations = set()

        for i in range(1, APP_CONFIG.max_bar_types + 1):
            possible_combinations.update(combinations(self.steel.available_sizes, i))

        return possible_combinations

    def choose_best_combination(self, combination: Tuple[float, ...]) -> Tuple[Rebar, ...]:
        """
        Choose the best combination of rebar sizes based on the required area and other criteria.

        :return: The best combination of rebar sizes.
        """
        # TODO implment coin dp for combo -> returning it in a dumb way for now
        necessary_bars = ceil(self.required_area / combination[0])
        bars = [Rebar(combination[0], self.steel) for _ in range(necessary_bars)]
        return tuple(bars)

    def get_best_solution_for_combo(self, combination: Tuple[float, ...]) -> Tuple[Rebar, ...]:
        """
        Get the best solution for a given combination of rebar sizes.

        :param combination: A tuple of rebar sizes.
        :return: A tuple with the best solution.
        """
        return self.solutions_per_diameter.get(combination, ())