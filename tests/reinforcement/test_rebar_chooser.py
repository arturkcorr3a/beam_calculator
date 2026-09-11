from typing import Tuple

import pytest

from src.config import APP_CONFIG
from src.structural_elements.rebar import Rebar
from src.properties.steel import Steel
from src.reinforcement.rebar_chooser import RebarChooser


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def total_area(rebars: Tuple[Rebar, ...]) -> float:
    return sum(r.area_cm2 for r in rebars)


# ---------------------------------------------------------------------------
# 1. possible_diameter_combinations
# ---------------------------------------------------------------------------

def test_possible_diameter_combinations_count_ca25() -> None:
    chooser = RebarChooser(Steel.CA25, 2.0)
    assert len(chooser.possible_diameter_combinations) == 175


def test_possible_diameter_combinations_count_ca50() -> None:
    chooser = RebarChooser(Steel.CA50, 2.0)
    assert len(chooser.possible_diameter_combinations) == 175


def test_possible_diameter_combinations_count_ca60() -> None:
    chooser = RebarChooser(Steel.CA60, 1.0)
    assert len(chooser.possible_diameter_combinations) == 298


@pytest.mark.parametrize("steel", [Steel.CA25, Steel.CA50])
def test_possible_diameter_combinations_all_single_sizes_ca25_ca50(steel: Steel) -> None:
    chooser = RebarChooser(steel, 2.0)
    for size in steel.available_sizes:
        assert (size,) in chooser.possible_diameter_combinations


def test_possible_diameter_combinations_all_single_sizes_ca60() -> None:
    chooser = RebarChooser(Steel.CA60, 1.0)
    for size in Steel.CA60.available_sizes:
        assert (size,) in chooser.possible_diameter_combinations


@pytest.mark.parametrize("steel,required_area", [
    (Steel.CA25, 2.0),
    (Steel.CA50, 2.0),
    (Steel.CA60, 1.0),
])
def test_possible_diameter_combinations_max_bar_types(steel: Steel, required_area: float) -> None:
    chooser = RebarChooser(steel, required_area)
    for combo in chooser.possible_diameter_combinations:
        assert len(combo) <= APP_CONFIG.max_bar_types


# ---------------------------------------------------------------------------
# 2. choose_best_combination — CA25
# ---------------------------------------------------------------------------

CA25_CASES: list[Tuple[Tuple[float, ...], float]] = [
    ((10,),        1.0),
    ((10,),        2.0),
    ((10,),        5.0),
    ((16,),        2.0),
    ((16,),        5.0),
    ((16,),        10.0),
    ((10, 16),     1.5),
    ((10, 16),     4.0),
    ((10, 16),     8.0),
    ((16, 20),     3.0),
    ((16, 20),     6.0),
    ((16, 20),     12.0),
    ((10, 16, 20), 2.0),
    ((10, 16, 20), 7.0),
    ((10, 16, 20), 13.0),
]


@pytest.mark.parametrize("combo,required_area", CA25_CASES)
def test_ca25_result_not_empty(combo: Tuple[float, ...], required_area: float) -> None:
    chooser = RebarChooser(Steel.CA25, required_area)
    result = chooser.choose_best_combination(combo)
    assert len(result) > 0


@pytest.mark.parametrize("combo,required_area", CA25_CASES)
def test_ca25_result_area_sufficient(combo: Tuple[float, ...], required_area: float) -> None:
    chooser = RebarChooser(Steel.CA25, required_area)
    result = chooser.choose_best_combination(combo)
    assert total_area(result) >= required_area - 0.01


@pytest.mark.parametrize("combo,required_area", CA25_CASES)
def test_ca25_result_min_two_bars(combo: Tuple[float, ...], required_area: float) -> None:
    chooser = RebarChooser(Steel.CA25, required_area)
    result = chooser.choose_best_combination(combo)
    assert len(result) >= 2


@pytest.mark.parametrize("combo,required_area", CA25_CASES)
def test_ca25_result_diameters_within_combo(combo: Tuple[float, ...], required_area: float) -> None:
    chooser = RebarChooser(Steel.CA25, required_area)
    result = chooser.choose_best_combination(combo)
    for rebar in result:
        assert rebar.diameter_mm in combo


# ---------------------------------------------------------------------------
# 3. choose_best_combination — CA50
# ---------------------------------------------------------------------------

CA50_CASES: list[Tuple[Tuple[float, ...], float]] = [
    ((10,),        1.0),
    ((10,),        2.0),
    ((10,),        5.0),
    ((16,),        2.0),
    ((16,),        5.0),
    ((16,),        10.0),
    ((10, 16),     1.5),
    ((10, 16),     4.0),
    ((10, 16),     8.0),
    ((16, 20),     3.0),
    ((16, 20),     6.0),
    ((16, 20),     12.0),
    ((10, 16, 20), 2.0),
    ((10, 16, 20), 7.0),
    ((10, 16, 20), 13.0),
]


@pytest.mark.parametrize("combo,required_area", CA50_CASES)
def test_ca50_result_not_empty(combo: Tuple[float, ...], required_area: float) -> None:
    chooser = RebarChooser(Steel.CA50, required_area)
    result = chooser.choose_best_combination(combo)
    assert len(result) > 0


@pytest.mark.parametrize("combo,required_area", CA50_CASES)
def test_ca50_result_area_sufficient(combo: Tuple[float, ...], required_area: float) -> None:
    chooser = RebarChooser(Steel.CA50, required_area)
    result = chooser.choose_best_combination(combo)
    assert total_area(result) >= required_area - 0.01


@pytest.mark.parametrize("combo,required_area", CA50_CASES)
def test_ca50_result_min_two_bars(combo: Tuple[float, ...], required_area: float) -> None:
    chooser = RebarChooser(Steel.CA50, required_area)
    result = chooser.choose_best_combination(combo)
    assert len(result) >= 2


@pytest.mark.parametrize("combo,required_area", CA50_CASES)
def test_ca50_result_diameters_within_combo(combo: Tuple[float, ...], required_area: float) -> None:
    chooser = RebarChooser(Steel.CA50, required_area)
    result = chooser.choose_best_combination(combo)
    for rebar in result:
        assert rebar.diameter_mm in combo


# ---------------------------------------------------------------------------
# 4. choose_best_combination — CA60
# ---------------------------------------------------------------------------

CA60_CASES: list[Tuple[Tuple[float, ...], float]] = [
    ((5.0,),          0.5),
    ((5.0,),          0.9),
    ((5.0,),          1.9),
    ((6.0,),          0.5),
    ((6.0,),          1.5),
    ((6.0,),          3.0),
    ((5.0, 6.0),      0.5),
    ((5.0, 6.0),      1.5),
    ((5.0, 6.0),      3.0),
    ((6.0, 8.0),      1.0),
    ((6.0, 8.0),      2.5),
    ((6.0, 8.0),      5.0),
    ((5.0, 6.0, 8.0), 1.0),
    ((5.0, 6.0, 8.0), 2.5),
    ((5.0, 6.0, 8.0), 5.0),
]


@pytest.mark.parametrize("combo,required_area", CA60_CASES)
def test_ca60_result_not_empty(combo: Tuple[float, ...], required_area: float) -> None:
    chooser = RebarChooser(Steel.CA60, required_area)
    result = chooser.choose_best_combination(combo)
    assert len(result) > 0


@pytest.mark.parametrize("combo,required_area", CA60_CASES)
def test_ca60_result_area_sufficient(combo: Tuple[float, ...], required_area: float) -> None:
    chooser = RebarChooser(Steel.CA60, required_area)
    result = chooser.choose_best_combination(combo)
    assert total_area(result) >= required_area - 0.01


@pytest.mark.parametrize("combo,required_area", CA60_CASES)
def test_ca60_result_min_two_bars(combo: Tuple[float, ...], required_area: float) -> None:
    chooser = RebarChooser(Steel.CA60, required_area)
    result = chooser.choose_best_combination(combo)
    assert len(result) >= 2


@pytest.mark.parametrize("combo,required_area", CA60_CASES)
def test_ca60_result_diameters_within_combo(combo: Tuple[float, ...], required_area: float) -> None:
    chooser = RebarChooser(Steel.CA60, required_area)
    result = chooser.choose_best_combination(combo)
    for rebar in result:
        assert rebar.diameter_mm in combo


# ---------------------------------------------------------------------------
# 5. get_best_solution_for_combo
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("steel,combo,required_area", [
    (Steel.CA25, (10, 16), 4.0),
    (Steel.CA50, (16, 20), 6.0),
    (Steel.CA60, (5.0, 6.0), 1.5),
])
def test_get_best_solution_for_known_combo(
    steel: Steel, combo: Tuple[float, ...], required_area: float
) -> None:
    chooser = RebarChooser(steel, required_area)
    result = chooser.get_best_solution_for_combo(combo)
    assert isinstance(result, tuple)
    assert len(result) >= 2


@pytest.mark.parametrize("steel,required_area", [
    (Steel.CA25, 4.0),
    (Steel.CA50, 6.0),
    (Steel.CA60, 1.5),
])
def test_get_best_solution_for_unknown_combo_returns_empty(steel: Steel, required_area: float) -> None:
    chooser = RebarChooser(steel, required_area)
    result = chooser.get_best_solution_for_combo((99.9, 88.8))
    assert result == ()


# ---------------------------------------------------------------------------
# 6. solutions_per_diameter completeness
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("steel,required_area", [
    (Steel.CA25, 4.0),
    (Steel.CA50, 6.0),
    (Steel.CA60, 1.5),
])
def test_solutions_per_diameter_keys_match_possible_combos(steel: Steel, required_area: float) -> None:
    chooser = RebarChooser(steel, required_area)
    assert set(chooser.solutions_per_diameter.keys()) == chooser.possible_diameter_combinations


@pytest.mark.parametrize("steel,required_area", [
    (Steel.CA25, 4.0),
    (Steel.CA50, 6.0),
    (Steel.CA60, 1.5),
])
def test_solutions_per_diameter_values_are_tuples(steel: Steel, required_area: float) -> None:
    chooser = RebarChooser(steel, required_area)
    for value in chooser.solutions_per_diameter.values():
        assert isinstance(value, tuple)


# ---------------------------------------------------------------------------
# 7. Edge cases
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("steel,combo", [
    (Steel.CA25, (10,)),
    (Steel.CA50, (16,)),
    (Steel.CA60, (5.0,)),
])
def test_very_small_required_area_still_yields_two_bars(steel: Steel, combo: Tuple[float, ...]) -> None:
    chooser = RebarChooser(steel, 0.01)
    result = chooser.choose_best_combination(combo)
    assert len(result) >= 2


@pytest.mark.parametrize("steel,combo", [
    (Steel.CA25, (10,)),
    (Steel.CA50, (16,)),
    (Steel.CA60, (5.0,)),
])
def test_single_diameter_combo_all_bars_same_diameter(steel: Steel, combo: Tuple[float, ...]) -> None:
    chooser = RebarChooser(steel, 2.0)
    result = chooser.choose_best_combination(combo)
    diameters = {r.diameter_mm for r in result}
    assert diameters == {combo[0]}