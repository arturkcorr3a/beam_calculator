"""Unit tests for src/calculators/stirrup_rebar_coordinator.py — coordinate_span()."""

import types
from collections.abc import Callable

import pytest

from src.calculators import stirrup_rebar_coordinator
from src.calculators.stirrup_rebar_coordinator import coordinate_span
from tests.helpers import assert_approx

# ---------------------------------------------------------------------------
# Test doubles
# ---------------------------------------------------------------------------


def _make_calculator_stub(d: float = 56.0) -> types.SimpleNamespace:
    """Return a RebarCalculator stub that records its calculate_for() inputs.

    Each calculate_for() call sets d to its initial value minus the stirrup
    diameter, mimicking the stirrup's effect on the effective depth (cm).
    """
    calculator = types.SimpleNamespace(d=d, base_d=d, calls=[])

    def calculate_for(stirrup_diameter: float, moment_shift: float) -> None:
        calculator.calls.append((stirrup_diameter, moment_shift))
        calculator.d = calculator.base_d - stirrup_diameter

    calculator.calculate_for = calculate_for
    return calculator


def _make_stirrups_stub(
    diameter_for: Callable[[float], float], moment_shift: float = 28.0
) -> types.SimpleNamespace:
    """Return a Stirrups stub that records the depths it is dimensioned with (cm).

    Args:
        diameter_for: Maps the effective depth (cm) to the chosen diameter (cm).
        moment_shift: Moment shift a_l (cm) returned by its calculator.
    """
    stirrups = types.SimpleNamespace(
        depths=[],
        calculator=types.SimpleNamespace(calculate_moment_shift=lambda: moment_shift),
    )

    def calculate_and_choose(effective_depth: float) -> tuple[float, float]:
        stirrups.depths.append(effective_depth)
        return 20.0, diameter_for(effective_depth)

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

    def test_propagates_diameter_and_moment_shift(self) -> None:
        """Every calculator receives the stirrup diameter and moment shift (cm)."""
        calculators = [_make_calculator_stub(), _make_calculator_stub(d=58.0)]
        stirrups = _make_stirrups_stub(lambda depth: 0.5, moment_shift=27.0)

        coordinate_span(calculators, stirrups)  # type: ignore[arg-type]

        for calculator in calculators:
            assert calculator.calls[-1] == (0.5, 27.0), (
                "calculate_for should receive (phi, a_l) from the stirrups"
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

        assert [diameter for diameter, _ in calculator.calls] == [0.8, 0.63, 0.63], (
            "rebars should be dimensioned with 0.8 cm, then 0.63 cm until d settles"
        )

    def test_raises_on_empty_list(self) -> None:
        """No calculators raises ValueError."""
        stirrups = _make_stirrups_stub(lambda depth: 0.5)

        with pytest.raises(ValueError, match="At least one rebar calculator"):
            coordinate_span([], stirrups)  # type: ignore[arg-type]

    def test_raises_when_not_converging(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """A d that keeps oscillating raises ValueError after MAX_ITERATIONS passes."""
        monkeypatch.setattr(stirrup_rebar_coordinator, "MAX_ITERATIONS", 5)
        calculator = _make_calculator_stub(d=56.0)
        # The diameter flips with d, so d never settles (cm)
        stirrups = _make_stirrups_stub(lambda depth: 1.0 if depth >= 55.5 else 0.5)

        with pytest.raises(ValueError, match="did not converge within 5"):
            coordinate_span([calculator], stirrups)  # type: ignore[list-item]
