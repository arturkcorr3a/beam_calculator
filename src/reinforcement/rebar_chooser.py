from collections import Counter
from functools import cached_property
from itertools import combinations
from math import ceil, floor

from src.config import APP_CONFIG
from src.logger import log_operation, log_property, logger_label
from src.properties.steel import Steel
from src.structural_elements.rebar import Rebar


@logger_label("Rebar Chooser - {label}")
class RebarChooser:
    """Select and store rebar solutions for a given steel grade and required area."""

    steel: Steel
    required_area: float
    solutions_per_diameter: dict[tuple[float, ...], tuple[Rebar, ...]]

    def __init__(self, steel: Steel, required_area: float):
        self.steel = steel
        self.required_area = required_area
        self.set_solutions_per_diameter()

    @property
    def label(self) -> str:
        return f"{self.steel.name} - {self.required_area:.2f} cm²"

    def set_solutions_per_diameter(self) -> None:
        """Build the cached best solution for each possible bar-diameter combination."""
        log_operation(
            f"Finding optimal rebar combinations for required area: {self.required_area:.2f} cm² ({self.steel.name})"
        )
        solutions: dict[tuple[float, ...], tuple[Rebar, ...]] = {}
        for combination in self.possible_diameter_combinations:
            solutions[combination] = self.choose_best_combination(combination)
        self.solutions_per_diameter = solutions

        valid_solutions = sum(1 for s in solutions.values() if s)
        log_property(
            f"Evaluated {len(solutions)} combinations: {valid_solutions} valid solutions found"
        )

    @cached_property
    def possible_diameter_combinations(self) -> list[tuple[float, ...]]:
        """Assemble all possible combinations of rebar diameters up to the configured maximum bar types."""
        unique_combinations: set[tuple[float, ...]] = set()

        for i in range(1, APP_CONFIG.max_bar_types + 1):
            unique_combinations.update(combinations(self.steel.available_sizes, i))
        possible_combinations = sorted(unique_combinations)

        log_property(f"Available steel sizes: {self.steel.available_sizes}")
        log_property(
            f"Generated {len(possible_combinations)} possible diameter combinations (max bar types: {APP_CONFIG.max_bar_types})"
        )
        return possible_combinations

    def choose_best_combination(
        self, combination: tuple[float, ...]
    ) -> tuple[Rebar, ...]:
        """Find the optimal bar combination for a fixed diameter subset using unbounded coin-change DP.

        Primary goal: minimum total area >= required_area.
        Secondary goal: fewest bars (minimized implicitly per DP step).
        Minimum bars: at least 2 bars in the output.

        Args:
            combination: Tuple of bar diameters (mm) forming the denomination set for this run.

        Returns:
            Tuple of Rebar instances satisfying the area and bar-count constraints, or an empty
            tuple if no valid combination can be found.
        """
        # Each bar's area is mapped to an integer slot count; slot * eps = area in cm²
        eps = 0.01  # discretization step, cm²

        # Build one Rebar per diameter and convert its area to an integer coin value,
        # rounded down so a slot never claims more area than its bars provide
        rebars: list[Rebar] = [Rebar(diameter, self.steel) for diameter in combination]
        coins = [floor(rebar.area_cm2 / eps) for rebar in rebars]

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

        combo_label = ", ".join(f"{d:g}mm" for d in combination)
        if best == -1:
            log_property(f"No valid combination found for diameters ({combo_label})")
            return ()

        # Walk the previous[] chain to reconstruct the chosen bars
        result: list[Rebar] = []
        slot = best
        while slot > 0:
            rebar_index = previous[slot]
            assert rebar_index != -1, f"Broken DP chain at slot {slot}"
            result.append(rebars[rebar_index])
            slot -= coins[rebar_index]

        total_area = sum(bar.area_cm2 for bar in result)
        counter = Counter(bar.diameter_mm for bar in result)
        bars_description = ", ".join(
            f"{count}x{diameter:g}mm" for diameter, count in sorted(counter.items())
        )
        log_property(
            f"Best combination for ({combo_label}): {bars_description} (area = {total_area:.2f} cm², bars = {len(result)})"
        )
        return tuple(result)

    @cached_property
    def ranked_solutions(self) -> tuple[tuple[Rebar, ...], ...]:
        """Rank the distinct solutions of every diameter subset, smallest area first

        Ties are broken by fewer bars, then fewer distinct diameters, then
        larger bars. Subsets that yield the same bar multi-set appear once.

        Returns:
            Solutions ordered from most to least preferred.
        """
        unique: dict[tuple[float, ...], tuple[Rebar, ...]] = {}
        for solution in self.solutions_per_diameter.values():
            if solution:
                key = tuple(sorted(bar.diameter_mm for bar in solution))
                unique.setdefault(key, solution)

        def rank(solution: tuple[Rebar, ...]) -> tuple[float, int, int, float]:
            diameters = [bar.diameter_mm for bar in solution]
            return (
                round(sum(bar.area_cm2 for bar in solution), 6),
                len(solution),
                len(set(diameters)),
                -max(diameters),
            )

        ranked = tuple(sorted(unique.values(), key=rank))
        log_property(f"Ranked {len(ranked)} distinct solutions by total area")
        return ranked

    def get_best_solution_for_combo(
        self, combination: tuple[float, ...]
    ) -> tuple[Rebar, ...]:
        """Get the precomputed best rebar solution for a given diameter combination.

        Args:
            combination: Tuple of bar diameters (mm).

        Returns:
            Tuple of Rebar instances, or an empty tuple if no solution exists.
        """
        solution = self.solutions_per_diameter.get(combination, ())
        combo_label = ", ".join(f"{d:g}mm" for d in combination)
        if solution:
            counter = Counter(b.diameter_mm for b in solution)
            bars_desc = ", ".join(
                f"{count}x{d:g}mm" for d, count in sorted(counter.items())
            )
            total_area = sum(b.area_cm2 for b in solution)
            log_property(
                f"Retrieved solution for ({combo_label}): {bars_desc} (area = {total_area:.2f} cm²)"
            )
        else:
            log_property(f"No cached solution found for ({combo_label})")
        return solution
