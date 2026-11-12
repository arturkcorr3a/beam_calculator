"""Unit tests for the RebarChooser diameter-combination solver."""

from collections.abc import Iterator

import pytest

from src.config import APP_CONFIG
from src.properties.steel import Steel
from src.reinforcement.rebar_chooser import CACHE_MARGIN, RebarChooser
from tests.helpers import assert_approx

REQUIRED_AREA = 4.0  # cm²


@pytest.fixture(autouse=True)
def fresh_chooser() -> Iterator[None]:
    """Start and end every test with an empty shared chooser"""
    RebarChooser.reset()
    yield
    RebarChooser.reset()


@pytest.fixture
def chooser() -> RebarChooser:
    """The shared chooser, with tables built for a CA50 4.0 cm² request"""
    chooser = RebarChooser.instance()
    chooser.solutions_per_diameter(Steel.CA50, REQUIRED_AREA)
    return chooser


class TestSingleton:
    """Tests for the shared-instance behaviour."""

    def test_same_instance(self) -> None:
        assert RebarChooser() is RebarChooser.instance(), (
            "Every construction should return the shared chooser"
        )

    def test_reset_drops_instance(self) -> None:
        first = RebarChooser.instance()
        RebarChooser.reset()
        assert RebarChooser.instance() is not first, (
            "Reset should make the next access build a new chooser"
        )


class TestLabel:
    """Tests for the human-readable chooser label."""

    def test_format(self, chooser: RebarChooser) -> None:
        assert chooser.label == "CA50 - cap 6.00 cm²", (
            "Label should combine steel grade with the cached capacity"
        )


class TestCache:
    """Tests for when the DP tables are reused or rebuilt."""

    def test_smaller_area_reuses_tables(self, chooser: RebarChooser) -> None:
        tables = chooser.tables
        chooser.ranked_solutions(Steel.CA50, 2.0)
        assert chooser.tables is tables, "A smaller area should reuse the tables"

    def test_area_within_margin_reuses_tables(self, chooser: RebarChooser) -> None:
        tables = chooser.tables
        chooser.ranked_solutions(Steel.CA50, CACHE_MARGIN * REQUIRED_AREA)
        assert chooser.tables is tables, (
            "An area up to the cached capacity should reuse the tables"
        )

    def test_larger_area_rebuilds(self, chooser: RebarChooser) -> None:
        tables = chooser.tables
        chooser.ranked_solutions(Steel.CA50, 10.0)
        assert chooser.tables is not tables, "An area over capacity should rebuild"
        assert_approx(
            chooser.capacity_area,
            CACHE_MARGIN * 10.0,
            "The new capacity should be the margin times the new area",
        )

    def test_steel_change_rebuilds(self, chooser: RebarChooser) -> None:
        tables = chooser.tables
        chooser.ranked_solutions(Steel.CA60, 2.0)
        assert chooser.tables is not tables, "A steel change should rebuild"

    def test_max_bar_types_change_rebuilds(
        self, chooser: RebarChooser, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        tables = chooser.tables
        monkeypatch.setattr(APP_CONFIG, "max_bar_types", 1)
        chooser.ranked_solutions(Steel.CA50, 2.0)
        assert chooser.tables is not tables, "A max bar types change should rebuild"
        assert len(chooser.tables) == 10, "One combination per available size"

    @pytest.mark.parametrize("area", [0.5, 2.0, 4.02, 7.3])
    def test_warm_matches_cold(self, area: float) -> None:
        chooser = RebarChooser.instance()
        chooser.ranked_solutions(Steel.CA50, 20.0)
        warm = chooser.ranked_solutions(Steel.CA50, area)
        RebarChooser.reset()
        cold = RebarChooser.instance().ranked_solutions(Steel.CA50, area)
        assert warm == cold, f"Cached tables should give the cold result for {area}"

    def test_fresh_bars_per_call(self, chooser: RebarChooser) -> None:
        first = chooser.get_best_solution_for_combo(Steel.CA50, 2.0, (12.5,))
        second = chooser.get_best_solution_for_combo(Steel.CA50, 2.0, (12.5,))
        assert first[0] is not second[0], (
            "Callers mutate bars, so each call should return new instances"
        )


class TestChooseBestCombination:
    """Tests for the unbounded coin-change bar selection."""

    def test_single_diameter_multi_bar(self, chooser: RebarChooser) -> None:
        solution = chooser.choose_best_combination(Steel.CA50, REQUIRED_AREA, (12.5,))
        assert len(solution) == 4, "Four 12.5 mm bars are the fewest reaching 4 cm²"
        assert_approx(
            sum(bar.area_cm2 for bar in solution),
            4.908738521234052,
            "Four 12.5 mm bars should total ~4.91 cm²",
        )

    def test_two_bar_minimum(self, chooser: RebarChooser) -> None:
        solution = chooser.choose_best_combination(Steel.CA50, REQUIRED_AREA, (32,))
        assert [bar.diameter_mm for bar in solution] == [32, 32], (
            "The two-bar minimum forces two 32 mm bars even when one overshoots"
        )

    def test_real_area_covers_required(self, chooser: RebarChooser) -> None:
        """Every solution covers the required area with unrounded areas (cm²)"""
        solutions = chooser.solutions_per_diameter(Steel.CA50, REQUIRED_AREA)
        for combination, solution in solutions.items():
            area = sum(bar.area_cm2 for bar in solution)
            assert area >= REQUIRED_AREA, (
                f"Solution for {combination} totals {area} cm² < 4.0 cm²"
            )


class TestRankedSolutions:
    """Tests for the global ranking across diameter combinations."""

    def test_minimum_area_first(self) -> None:
        best = RebarChooser.instance().ranked_solutions(Steel.CA50, 2.0)[0]
        assert sorted(bar.diameter_mm for bar in best) == [8, 8, 8, 8], (
            "Four 8 mm bars give the smallest area reaching 2.0 cm²"
        )
        assert_approx(
            sum(bar.area_cm2 for bar in best),
            2.0106192982974678,
            "Four 8 mm bars should total ~2.01 cm²",
        )

    def test_sorted_by_area(self, chooser: RebarChooser) -> None:
        areas = [
            sum(bar.area_cm2 for bar in solution)
            for solution in chooser.ranked_solutions(Steel.CA50, REQUIRED_AREA)
        ]
        assert areas == sorted(areas), "Solutions should be ordered by total area"

    def test_no_duplicate_bar_sets(self, chooser: RebarChooser) -> None:
        keys = [
            tuple(sorted(bar.diameter_mm for bar in solution))
            for solution in chooser.ranked_solutions(Steel.CA50, REQUIRED_AREA)
        ]
        assert len(keys) == len(set(keys)), (
            "Combinations yielding the same bars should appear once"
        )

    def test_tie_prefers_fewer_bars(self) -> None:
        """2x16mm and 8x8mm both total 4.02 cm²; the fewer bars rank first"""
        best = RebarChooser.instance().ranked_solutions(Steel.CA50, 4.02)[0]
        assert [bar.diameter_mm for bar in best] == [16, 16], (
            "On equal area, two 16 mm bars should beat eight 8 mm bars"
        )


class TestPossibleDiameterCombinations:
    """Tests for the generated diameter-combination set."""

    def test_count_default_config(self) -> None:
        assert len(RebarChooser.possible_diameter_combinations(Steel.CA50)) == 175, (
            "Ten sizes across up to three bar types yield 175 combinations"
        )

    def test_respects_max_bar_types(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setattr(APP_CONFIG, "max_bar_types", 1)
        assert len(RebarChooser.possible_diameter_combinations(Steel.CA50)) == 10, (
            "Limiting to one bar type yields one combination per available size"
        )


class TestGetBestSolutionForCombo:
    """Tests for retrieving the solution for a combination."""

    def test_hit_returns_solution(self, chooser: RebarChooser) -> None:
        solution = chooser.get_best_solution_for_combo(
            Steel.CA50, REQUIRED_AREA, (12.5,)
        )
        assert len(solution) == 4, "The (12.5,) solution should be four bars"

    def test_miss_returns_empty(self, chooser: RebarChooser) -> None:
        solution = chooser.get_best_solution_for_combo(
            Steel.CA50, REQUIRED_AREA, (6.3, 8, 10, 12.5)
        )
        assert solution == (), "A combination never generated has no solution"
