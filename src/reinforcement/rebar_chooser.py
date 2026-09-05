from functools import cached_property
from itertools import combinations
from math import ceil

from src.config import APP_CONFIG
from src.elements.rebar import Rebar
from src.properties.steel import Steel


class RebarChooser:
    """Select and store rebar solutions for a given steel grade and required area."""

    steel: Steel
    required_area: float
    solutions_per_diameter: dict[tuple[float, ...], tuple[Rebar, ...]]

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
    def possible_diameter_combinations(self) -> set[tuple[float, ...]]:
        """
        Assemble all possible combinations of rebar sizes that do not exceed the maximum length.

        :param rebar_sizes: List of available rebar sizes (lengths).
        :return: List of valid combinations of rebar sizes.
        """
        possible_combinations: set[tuple[float, ...]] = set()

        for i in range(1, APP_CONFIG.max_bar_types + 1):
            possible_combinations.update(combinations(self.steel.available_sizes, i))

        return possible_combinations

    # PAPER get reference for the coin change problem and how it works for this case
    def choose_best_combination(
        self, combination: tuple[float, ...]
    ) -> tuple[Rebar, ...]:
        """
        Find the optimal bar combination for a fixed diameter subset using unbounded coin-change DP.

        Primary goal  : minimum total area >= required_area.
        Secondary goal: fewest bars (enforced implicitly by minimizing bar count at each DP step).
        Minimum bars  : at least 2 bars in the output.

        :param combination: Tuple of bar diameters (mm) forming the denomination set for this run.
        :return: Tuple of Rebar instances (with repetition) satisfying the area and bar-count constraints, or an empty tuple if no valid combination can be found.
        """
        # Each bar's area is mapped to an integer slot count; slot * eps = area in cm²
        eps = 0.01  # discretization step, cm²

        # Build one Rebar per diameter and convert its area to an integer coin value
        rebars: list[Rebar] = [Rebar(diameter, self.steel) for diameter in combination]
        coins = [round(rebar.area_cm2 / eps) for rebar in rebars]

        # The DP table must cover at least the required area plus room to overshoot
        # by one full coin, and must be large enough to host a 2-bar solution
        start = ceil(self.required_area / eps)
        max_coin = max(coins)
        table_size = max(start + max_coin, 2 * max_coin) + 1

        # dp[slot] = minimum bars to reach exactly slot * eps cm²; previous[slot] = coin index used
        INFINITE = float("inf")
        dp = [INFINITE] * table_size
        previous = [-1] * table_size
        dp[0] = 0

        # Standard unbounded coin-change fill: try every coin at every slot
        for slot in range(1, table_size):
            for rebar_index, coin in enumerate(coins):
                if coin <= slot and dp[slot - coin] + 1 < dp[slot]:
                    dp[slot] = dp[slot - coin] + 1
                    previous[slot] = rebar_index

        # Find the first reachable slot >= start that uses at least 2 bars
        best = -1
        for slot in range(start, table_size):
            if dp[slot] != INFINITE and dp[slot] >= 2:
                best = slot
                break

        if best == -1:
            return ()

        # Walk the previous[] chain to reconstruct the chosen bars
        result: list[Rebar] = []
        slot = best
        while slot > 0:
            rebar_index = previous[slot]
            result.append(rebars[rebar_index])
            slot -= coins[rebar_index]
        return tuple(result)

    def get_best_solution_for_combo(
        self, combination: tuple[float, ...]
    ) -> tuple[Rebar, ...]:
        """
        Get the best solution for a given combination of rebar sizes.

        :param combination: A tuple of rebar sizes.
        :return: A tuple with the best solution.
        """
        return self.solutions_per_diameter.get(combination, ())
