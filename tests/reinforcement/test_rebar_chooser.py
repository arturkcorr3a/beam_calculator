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
