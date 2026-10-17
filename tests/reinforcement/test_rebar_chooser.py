"""Unit tests for the RebarChooser diameter-combination solver."""

import pytest

from src.config import APP_CONFIG
from src.properties.steel import Steel
from src.reinforcement.rebar_chooser import RebarChooser
from tests.helpers import assert_approx


@pytest.fixture
def chooser() -> RebarChooser:
    """Build a CA50 chooser targeting a 4.0 cm² required area.

    Construction runs the full DP over every diameter combination, so this
    fixture exercises ``__init__``, ``set_solutions_per_diameter``,
    ``possible_diameter_combinations``, and ``choose_best_combination``.
    """
    return RebarChooser(Steel.CA50, 4.0)


class TestLabel:
    """Tests for the human-readable chooser label."""

    def test_format(self, chooser: RebarChooser) -> None:
        assert chooser.label == "CA50 - 4.00 cm²", (
            "Label should combine steel grade with the area to two decimals"
        )


class TestChooseBestCombination:
    """Tests for the unbounded coin-change bar selection."""

    def test_single_diameter_multi_bar(self, chooser: RebarChooser) -> None:
        solution = chooser.choose_best_combination((12.5,))
        assert len(solution) == 4, "Four 12.5 mm bars are the fewest reaching 4 cm²"
        assert_approx(
            sum(bar.area_cm2 for bar in solution),
            4.908738521234052,
            "Four 12.5 mm bars should total ~4.91 cm²",
        )

    def test_two_bar_minimum(self, chooser: RebarChooser) -> None:
        solution = chooser.choose_best_combination((32,))
        assert [bar.diameter_mm for bar in solution] == [32, 32], (
            "The two-bar minimum forces two 32 mm bars even when one overshoots"
        )

    def test_real_area_covers_required(self, chooser: RebarChooser) -> None:
        """Every cached solution covers the required area with unrounded areas (cm²)"""
        for combination, solution in chooser.solutions_per_diameter.items():
            area = sum(bar.area_cm2 for bar in solution)
            assert area >= chooser.required_area, (
                f"Solution for {combination} totals {area} cm² < 4.0 cm²"
            )


class TestRankedSolutions:
    """Tests for the global ranking across diameter combinations."""

    def test_minimum_area_first(self) -> None:
        chooser = RebarChooser(Steel.CA50, 2.0)
        best = chooser.ranked_solutions[0]
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
            for solution in chooser.ranked_solutions
        ]
        assert areas == sorted(areas), "Solutions should be ordered by total area"

    def test_no_duplicate_bar_sets(self, chooser: RebarChooser) -> None:
        keys = [
            tuple(sorted(bar.diameter_mm for bar in solution))
            for solution in chooser.ranked_solutions
        ]
        assert len(keys) == len(set(keys)), (
            "Combinations yielding the same bars should appear once"
        )

    def test_tie_prefers_fewer_bars(self) -> None:
        """2x16mm and 8x8mm both total 4.02 cm²; the fewer bars rank first"""
        chooser = RebarChooser(Steel.CA50, 4.02)
        best = chooser.ranked_solutions[0]
        assert [bar.diameter_mm for bar in best] == [16, 16], (
            "On equal area, two 16 mm bars should beat eight 8 mm bars"
        )


class TestPossibleDiameterCombinations:
    """Tests for the generated diameter-combination set."""

    def test_count_default_config(self, chooser: RebarChooser) -> None:
        assert len(chooser.possible_diameter_combinations) == 175, (
            "Ten sizes across up to three bar types yield 175 combinations"
        )

    def test_respects_max_bar_types(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setattr(APP_CONFIG, "max_bar_types", 1)
        chooser = RebarChooser(Steel.CA50, 4.0)
        assert len(chooser.possible_diameter_combinations) == 10, (
            "Limiting to one bar type yields one combination per available size"
        )


class TestGetBestSolutionForCombo:
    """Tests for retrieving the precomputed solution for a combination."""

    def test_hit_returns_solution(self, chooser: RebarChooser) -> None:
        solution = chooser.get_best_solution_for_combo((12.5,))
        assert len(solution) == 4, "The cached (12.5,) solution should be four bars"

    def test_miss_returns_empty(self, chooser: RebarChooser) -> None:
        assert chooser.get_best_solution_for_combo((6.3, 8, 10, 12.5)) == (), (
            "A combination never generated has no cached solution"
        )
