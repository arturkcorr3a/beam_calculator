"""Unit tests for src/calculators/stirrup_rebar_coordinator.py — coordinate_span()."""

import types
from collections.abc import Callable
from math import pi

import pytest

from src.calculators import stirrup_rebar_coordinator
from src.calculators.stirrup_rebar_coordinator import coordinate_span
from src.errors import EffectiveDepthDivergedError
from tests.helpers import assert_approx

_DESIGN_SHEAR = 150.0  # kN, V_d returned by the stirrups' calculator

# ---------------------------------------------------------------------------
# Test doubles
# ---------------------------------------------------------------------------


def _make_calculator_stub(d: float = 56.0) -> types.SimpleNamespace:
    """Return a RebarCalculator stub that records its calculate_for() inputs.

    Each calculate_for() call sets d to its initial value minus the stirrup
    diameter, mimicking the stirrup's effect on the effective depth (cm).
    """
    calculator = types.SimpleNamespace(d=d, base_d=d, calls=[])

    def calculate_for(
        stirrup_diameter: float, moment_shift: float, design_shear: float
    ) -> None:
        calculator.calls.append((stirrup_diameter, moment_shift, design_shear))
        calculator.d = calculator.base_d - stirrup_diameter

    calculator.calculate_for = calculate_for
    return calculator


def _make_stirrups_stub(
    diameter_for: Callable[[float], float],
    moment_shift: float = 28.0,
    spacing_for: Callable[[float], float] = lambda depth: 20.0,
    required_ratio_for: Callable[[float], float] = lambda depth: 0.0,
) -> types.SimpleNamespace:
    """Return a Stirrups stub that records the depths it is dimensioned with (cm).

    Args:
        diameter_for: Maps the effective depth (cm) to the chosen diameter (cm).
        moment_shift: Moment shift a_l (cm) returned by its calculator.
        spacing_for: Maps the effective depth (cm) to the chosen spacing (cm).
        required_ratio_for: Maps the effective depth (cm) to the required A_sw/s (cm²/cm).
    """
    stirrups = types.SimpleNamespace(
        depths=[],
        required_ratio=0.0,
        calculator=types.SimpleNamespace(
            calculate_moment_shift=lambda: moment_shift,
            design_shear_force=_DESIGN_SHEAR,
        ),
    )

    def calculate_and_choose(effective_depth: float) -> tuple[float, float]:
        stirrups.depths.append(effective_depth)
        stirrups.required_ratio = required_ratio_for(effective_depth)
        return spacing_for(effective_depth), diameter_for(effective_depth)

    stirrups.calculate_and_choose = calculate_and_choose
    return stirrups


# ---------------------------------------------------------------------------
# TestCoordinateSpan
# ---------------------------------------------------------------------------


class TestCoordinateSpan:
    """Tests for coordinate_span() — the stirrup ↔ longitudinal reinforcement loop."""

    def test_stirrups_use_smallest_d(self) -> None:
        """The stirrups are first dimensioned with the smallest initial d (cm)."""
        calculators = [_make_calculator_stub(d=56.0), _make_calculator_stub(d=54.0)]
        stirrups = _make_stirrups_stub(lambda depth: 0.5)

        coordinate_span(calculators, stirrups)  # type: ignore[arg-type]

        assert_approx(stirrups.depths[0], 54.0, "min of d = 56 and d = 54 (cm)")

    def test_stirrups_re_dimensioned_with_resulting_d(self) -> None:
        """After the rebars, the stirrups are re-dimensioned with the new d (cm)."""
        calculator = _make_calculator_stub(d=56.0)
        stirrups = _make_stirrups_stub(lambda depth: 0.5)

        coordinate_span([calculator], stirrups)  # type: ignore[list-item]

        assert_approx(stirrups.depths[1], 55.5, "re-dimensioned with d - phi (cm)")

    def test_propagates_diameter_moment_shift_and_design_shear(self) -> None:
        """Every calculator receives the stirrup diameter, moment shift (cm) and V_d (kN)."""
        calculators = [_make_calculator_stub(), _make_calculator_stub(d=58.0)]
        stirrups = _make_stirrups_stub(lambda depth: 0.5, moment_shift=27.0)

        coordinate_span(calculators, stirrups)  # type: ignore[arg-type]

        for calculator in calculators:
            assert calculator.calls[-1] == (0.5, 27.0, _DESIGN_SHEAR), (
                "calculate_for should receive (phi, a_l, V_d) from the stirrups"
            )

    def test_stops_when_d_converges(self) -> None:
        """An unchanged d after the second pass ends the loop."""
        calculator = _make_calculator_stub()
        stirrups = _make_stirrups_stub(lambda depth: 0.5)

        coordinate_span([calculator], stirrups)  # type: ignore[list-item]

        assert len(calculator.calls) == 2, "rebars should be dimensioned twice"

    def test_re_dimensions_when_diameter_changes(self) -> None:
        """A diameter change dimensions the rebars again with the new diameter (cm)."""
        calculator = _make_calculator_stub(d=56.0)
        # 0.8 cm at the initial depth (56 cm), 0.63 cm once d drops below it
        stirrups = _make_stirrups_stub(lambda depth: 0.8 if depth >= 56.0 else 0.63)

        coordinate_span([calculator], stirrups)  # type: ignore[list-item]

        assert [diameter for diameter, _, _ in calculator.calls] == [0.8, 0.63, 0.63], (
            "rebars should be dimensioned with 0.8 cm, then 0.63 cm until d settles"
        )

    def test_raises_on_empty_list(self) -> None:
        """No calculators raises ValueError."""
        stirrups = _make_stirrups_stub(lambda depth: 0.5)

        with pytest.raises(ValueError, match="At least one rebar calculator"):
            coordinate_span([], stirrups)  # type: ignore[arg-type]

    def test_raises_when_not_converging(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """A d that keeps drifting without repeating a state raises ValueError after MAX_ITERATIONS passes."""
        monkeypatch.setattr(stirrup_rebar_coordinator, "MAX_ITERATIONS", 5)
        calculator = _make_calculator_stub(d=56.0)

        def drifting_calculate_for(
            stirrup_diameter: float, moment_shift: float, design_shear: float
        ) -> None:
            calculator.d -= 1.0  # cm, never settles nor repeats

        calculator.calculate_for = drifting_calculate_for
        stirrups = _make_stirrups_stub(lambda depth: 0.5)

        with pytest.raises(
            EffectiveDepthDivergedError, match="did not converge within 5"
        ):
            coordinate_span([calculator], stirrups)  # type: ignore[list-item]

    def test_same_stirrups_with_moving_d_is_not_a_cycle(self) -> None:
        """The same stirrups with a d that is still changing keep iterating (cm)."""
        calculator = _make_calculator_stub(d=56.0)
        depths_after = iter([55.0, 54.0, 54.0, 54.0])

        def calculate_for(
            stirrup_diameter: float, moment_shift: float, design_shear: float
        ) -> None:
            calculator.d = next(depths_after)

        calculator.calculate_for = calculate_for
        stirrups = _make_stirrups_stub(lambda depth: 0.5)

        coordinate_span([calculator], stirrups)  # type: ignore[list-item]

        assert stirrups.depths == [56.0, 55.0, 54.0], (
            "should stop on convergence, not on the repeated stirrups"
        )


# 6.3 mm every 13 cm and 8 mm every 20 cm: nearly equal A_sw/s (cm²/cm)
_THIN = (13.0, 0.63)
_THICK = (20.0, 0.8)


def _make_oscillating_case(
    required_at_low_d: float, required_at_high_d: float
) -> tuple[types.SimpleNamespace, types.SimpleNamespace]:
    """Return a calculator and stirrups that flip between the thick and thin stirrups

    The thick stirrups lower d (cm) and the thin ones raise it, like in a real beam; the
    A_sw/s required (cm²/cm) at the low d (thick stirrups' own d) and at the high d (thin
    stirrups' own d) make each state (un)safe.
    """
    calculator = _make_calculator_stub(d=85.0)
    d_for = {0.8: 84.19, 0.63: 85.97}

    def calculate_for(
        stirrup_diameter: float, moment_shift: float, design_shear: float
    ) -> None:
        calculator.calls.append((stirrup_diameter, moment_shift, design_shear))
        calculator.d = d_for[stirrup_diameter]

    calculator.calculate_for = calculate_for
    stirrups = _make_stirrups_stub(
        lambda depth: 0.63 if depth < 85.0 else 0.8,
        spacing_for=lambda depth: _THIN[0] if depth < 85.0 else _THICK[0],
        required_ratio_for=lambda depth: (
            required_at_low_d if depth < 85.0 else required_at_high_d
        ),
    )
    return calculator, stirrups


class TestCycle:
    """Tests for the stirrup ↔ longitudinal cycle resolution of coordinate_span()."""

    def test_oscillation_ends_without_error(self) -> None:
        """A two-state oscillation is resolved instead of raising ValueError."""
        calculator, stirrups = _make_oscillating_case(0.0, 0.0)

        coordinate_span([calculator], stirrups)  # type: ignore[list-item]

        assert len(calculator.calls) < 10, (
            "the cycle should be detected within a few passes"
        )

    def test_keeps_cheapest_safe_stirrups(self) -> None:
        """Both states cover their own requirement: the one with the smaller A_sw/s is kept."""
        calculator, stirrups = _make_oscillating_case(0.04, 0.04)

        coordinate_span([calculator], stirrups)  # type: ignore[list-item]

        # 6.3 mm every 13 cm has the smaller A_sw/s than 8 mm every 20 cm?
        thin = pi * (0.63 / 2) ** 2 * 2 / _THIN[0]
        thick = pi * (0.8 / 2) ** 2 * 2 / _THICK[0]
        expected = 0.63 if thin < thick else 0.8
        assert calculator.calls[-1][0] == expected, "cheapest safe stirrups are kept"

    def test_keeps_the_safe_one_when_only_one_is_safe(self) -> None:
        """Only the thick stirrups cover the A_sw/s required at their own d: they are kept."""
        calculator, stirrups = _make_oscillating_case(0.0, 1.0)

        coordinate_span([calculator], stirrups)  # type: ignore[list-item]

        assert calculator.calls[-1][0] == 0.8, "thin stirrups fall short at their own d"

    def test_unsafe_cycle_keeps_largest_and_warns(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """No safe stirrups: the largest A_sw/s is kept and a warning is logged."""
        warnings: list[str] = []
        monkeypatch.setattr(stirrup_rebar_coordinator, "log_general", warnings.append)
        calculator, stirrups = _make_oscillating_case(1.0, 1.0)

        coordinate_span([calculator], stirrups)  # type: ignore[list-item]

        thin = pi * (0.63 / 2) ** 2 * 2 / _THIN[0]
        thick = pi * (0.8 / 2) ** 2 * 2 / _THICK[0]
        assert calculator.calls[-1][0] == (0.63 if thin > thick else 0.8)
        assert len(warnings) == 1 and "WARNING" in warnings[0]
