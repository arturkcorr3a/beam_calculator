from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
from itertools import combinations
from math import ceil, floor
from typing import ClassVar

from src.config import APP_CONFIG
from src.logger import log_operation, log_property, logger_label
from src.properties.steel import Steel
from src.structural_elements.rebar import Rebar

CACHE_MARGIN = 1.5  # DP tables cover this multiple of the area that triggered the build
EPS = 0.01  # discretization step, cm²; slot * EPS = area in cm²
_INFINITE = float("inf")


@dataclass(frozen=True, slots=True)
class _DpTable:
    """Unbounded coin-change table for one diameter combination

    Attributes:
        diameters: Bar diameters (mm), one per coin.
        coins: Bar areas as integer slot counts, rounded down.
        dp: Minimum bars to reach exactly slot * EPS cm².
        previous: Coin index used to reach each slot, -1 if unreachable.
    """

    diameters: tuple[float, ...]
    coins: tuple[int, ...]
    dp: list[float]
    previous: list[int]


@logger_label("Rebar Chooser - {label}")
class RebarChooser:
    """Select rebar solutions for a steel grade and required area

    A singleton holding one DP table per diameter combination. The tables
    are built for CACHE_MARGIN times the requested area and reused for any
    later request that fits, until the steel, the maximum bar types, or a
    larger area forces a rebuild.
    """

    _instance: ClassVar[RebarChooser | None] = None

    _initialized: bool
    _steel: Steel | None
    _max_bar_types: int | None
    _capacity_area: float
    _tables: dict[tuple[float, ...], _DpTable]

    def __new__(cls) -> RebarChooser:
        if cls._instance is None:
            instance = super().__new__(cls)
            instance._initialized = False
            cls._instance = instance
        return cls._instance

    def __init__(self) -> None:
        if self._initialized:
            return
        self._initialized = True
        self._steel = None
        self._max_bar_types = None
        self._capacity_area = 0.0
        self._tables = {}

    @classmethod
    def instance(cls) -> RebarChooser:
        """Return the shared chooser"""
        return cls()

    @classmethod
    def reset(cls) -> None:
        """Drop the shared chooser and its cached tables"""
        cls._instance = None

    @property
    def label(self) -> str:
        steel_name = self._steel.name if self._steel is not None else "empty"
        return f"{steel_name} - cap {self._capacity_area:.2f} cm²"

    @property
    def capacity_area(self) -> float:
        """Largest required area the cached tables answer (cm²)"""
        return self._capacity_area

    @property
    def tables(self) -> dict[tuple[float, ...], _DpTable]:
        """Cached DP tables keyed by diameter combination"""
        return self._tables

    @staticmethod
    def possible_diameter_combinations(steel: Steel) -> list[tuple[float, ...]]:
        """Assemble all combinations of the steel's diameters up to the configured maximum bar types"""
        unique_combinations: set[tuple[float, ...]] = set()
        for i in range(1, APP_CONFIG.max_bar_types + 1):
            unique_combinations.update(combinations(steel.available_sizes, i))
        return sorted(unique_combinations)

    def _ensure_tables(self, steel: Steel, required_area: float) -> None:
        """Rebuild the DP tables unless the cached ones cover this request

        Args:
            steel: Steel grade of the request.
            required_area: Required area of the request (cm²).
        """
        if steel != self._steel:
            reason = f"steel changed to {steel.name}"
        elif APP_CONFIG.max_bar_types != self._max_bar_types:
            reason = f"max bar types changed to {APP_CONFIG.max_bar_types}"
        elif required_area > self._capacity_area:
            reason = f"{required_area:.2f} cm² exceeds capacity {self._capacity_area:.2f} cm²"
        else:
            log_property(
                f"Reusing cached tables for {required_area:.2f} cm² (capacity {self._capacity_area:.2f} cm²)"
            )
            return

        capacity_area = CACHE_MARGIN * required_area
        log_operation(
            f"Rebuilding rebar tables ({reason}); new capacity {capacity_area:.2f} cm²"
        )
        possible_combinations = self.possible_diameter_combinations(steel)
        log_property(f"Available steel sizes: {steel.available_sizes}")
        log_property(
            f"Generated {len(possible_combinations)} possible diameter combinations (max bar types: {APP_CONFIG.max_bar_types})"
        )
        self._tables = {
            combination: self._build_table(steel, combination, capacity_area)
            for combination in possible_combinations
        }
        self._steel = steel
        self._max_bar_types = APP_CONFIG.max_bar_types
        self._capacity_area = capacity_area

    @staticmethod
    def _build_table(
        steel: Steel, combination: tuple[float, ...], capacity_area: float
    ) -> _DpTable:
        """Fill the unbounded coin-change table for one diameter combination

        Args:
            steel: Steel grade of the bars.
            combination: Bar diameters (mm) forming the denomination set.
            capacity_area: Largest required area the table must answer (cm²).

        Returns:
            The filled table, large enough for any request up to capacity_area.
        """
        # Rounded down so a slot never claims more area than its bars provide
        coins = tuple(
            floor(Rebar(diameter, steel).area_cm2 / EPS) for diameter in combination
        )

        # Cover the capacity plus room to overshoot by one full coin, and
        # be large enough to host a 2-bar solution
        start = ceil(capacity_area / EPS)
        max_coin = max(coins)
        table_size = max(start + max_coin, 2 * max_coin) + 1

        dp: list[float] = [_INFINITE] * table_size
        previous = [-1] * table_size
        dp[0] = 0

        for slot in range(1, table_size):
            for rebar_index, coin in enumerate(coins):
                if coin <= slot and dp[slot - coin] + 1 < dp[slot]:
                    dp[slot] = dp[slot - coin] + 1
                    previous[slot] = rebar_index

        return _DpTable(combination, coins, dp, previous)

    def _pick(
        self, steel: Steel, table: _DpTable, required_area: float
    ) -> tuple[Rebar, ...]:
        """Read the best solution for an area from a filled table

        Primary goal: minimum total area >= required_area.
        Secondary goal: fewest bars.
        Minimum bars: at least 2 bars in the output.

        Fresh Rebar instances are built on every call, because callers set
        lengths and hooks on the bars they receive.

        Args:
            steel: Steel grade of the bars.
            table: Table filled for a capacity >= required_area.
            required_area: Required area (cm²).

        Returns:
            The chosen bars, or an empty tuple if no valid combination exists.
        """
        start = ceil(required_area / EPS)
        best = -1
        for slot in range(start, len(table.dp)):
            if table.dp[slot] != _INFINITE and table.dp[slot] >= 2:
                best = slot
                break

        combo_label = ", ".join(f"{d:g}mm" for d in table.diameters)
        if best == -1:
            log_property(f"No valid combination found for diameters ({combo_label})")
            return ()

        rebars = [Rebar(diameter, steel) for diameter in table.diameters]
        result: list[Rebar] = []
        slot = best
        while slot > 0:
            rebar_index = table.previous[slot]
            assert rebar_index != -1, f"Broken DP chain at slot {slot}"
            result.append(rebars[rebar_index])
            slot -= table.coins[rebar_index]

        total_area = sum(bar.area_cm2 for bar in result)
        counter = Counter(bar.diameter_mm for bar in result)
        bars_description = ", ".join(
            f"{count}x{diameter:g}mm" for diameter, count in sorted(counter.items())
        )
        log_property(
            f"Best combination for ({combo_label}): {bars_description} (area = {total_area:.2f} cm², bars = {len(result)})"
        )
        return tuple(result)

    def choose_best_combination(
        self, steel: Steel, required_area: float, combination: tuple[float, ...]
    ) -> tuple[Rebar, ...]:
        """Find the optimal bars for one diameter combination

        Args:
            steel: Steel grade of the bars.
            required_area: Required area (cm²).
            combination: Bar diameters (mm), one of the possible combinations.

        Returns:
            The chosen bars, or an empty tuple if none is valid or the
            combination is not one of the possible ones.
        """
        self._ensure_tables(steel, required_area)
        table = self._tables.get(combination)
        if table is None:
            combo_label = ", ".join(f"{d:g}mm" for d in combination)
            log_property(f"No cached solution found for ({combo_label})")
            return ()
        return self._pick(steel, table, required_area)

    def get_best_solution_for_combo(
        self, steel: Steel, required_area: float, combination: tuple[float, ...]
    ) -> tuple[Rebar, ...]:
        """Get the best rebar solution for a given diameter combination

        Args:
            steel: Steel grade of the bars.
            required_area: Required area (cm²).
            combination: Tuple of bar diameters (mm).

        Returns:
            Tuple of Rebar instances, or an empty tuple if no solution exists.
        """
        return self.choose_best_combination(steel, required_area, combination)

    def solutions_per_diameter(
        self, steel: Steel, required_area: float
    ) -> dict[tuple[float, ...], tuple[Rebar, ...]]:
        """Best solution of every possible diameter combination

        Args:
            steel: Steel grade of the bars.
            required_area: Required area (cm²).

        Returns:
            Solutions keyed by diameter combination; empty where none is valid.
        """
        log_operation(
            f"Finding optimal rebar combinations for required area: {required_area:.2f} cm² ({steel.name})"
        )
        self._ensure_tables(steel, required_area)
        solutions = {
            combination: self._pick(steel, table, required_area)
            for combination, table in self._tables.items()
        }
        valid_solutions = sum(1 for s in solutions.values() if s)
        log_property(
            f"Evaluated {len(solutions)} combinations: {valid_solutions} valid solutions found"
        )
        return solutions

    def ranked_solutions(
        self, steel: Steel, required_area: float
    ) -> tuple[tuple[Rebar, ...], ...]:
        """Rank the distinct solutions of every diameter subset, smallest area first

        Ties are broken by fewer bars, then fewer distinct diameters, then
        larger bars. Subsets that yield the same bar multi-set appear once.

        Args:
            steel: Steel grade of the bars.
            required_area: Required area (cm²).

        Returns:
            Solutions ordered from most to least preferred.
        """
        unique: dict[tuple[float, ...], tuple[Rebar, ...]] = {}
        for solution in self.solutions_per_diameter(steel, required_area).values():
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
