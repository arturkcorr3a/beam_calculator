"""Bastos (UNESP), item 19.7 — flexural reinforcement of beam VS1.

FROZEN: inputs and expected values come from docs/unesp-examples/vs1.md.
The moments are the book's redistributed values (delta = 0.85 at P2), taken as
inputs because the engine does not redistribute moments. The effective depth is
preset to the book's, so the comparison isolates the area calculation. The book
reads K_s from a rounded table, hence the 3 % tolerance (K_s = 0.023 is printed with two significant digits, which alone is worth about 2 %).
"""

import pytest

from src.calculators.rebar_calculator import RebarCalculator
from src.config import APP_CONFIG
from src.config_options import Aggregate
from src.properties.concrete import Concrete
from src.properties.steel import Steel
from src.structural_elements.rectangular_beam import RectangularBeam
from tests.helpers import assert_approx

LENGTH = 1432.5  # cm
STIRRUP_DIAMETER = 0.5  # cm
KN_M_PER_KN_CM = 0.01
TABLE_TOLERANCE = 0.03  # 3 %, the book's K_s table is rounded
MINIMUM_AREA = 1.71  # cm2, 0.15 % of 19 x 60 cm


@pytest.fixture(autouse=True)
def book_inputs(monkeypatch: pytest.MonkeyPatch) -> None:
    """Set the materials of the example (C30, basalt aggregate)"""
    monkeypatch.setattr(APP_CONFIG, "pavement_concrete", Concrete.C30)
    monkeypatch.setattr(APP_CONFIG, "aggregate", Aggregate.BASALT)


def _required_area(moment_kn_cm: float, position: float, depth: float) -> float:
    """Required tensioned area (cm2) for a characteristic moment given in kN.cm"""
    beam = RectangularBeam(length=LENGTH, width=19, height=60, steel=Steel.CA50)
    calculator = RebarCalculator(
        beam=beam,
        bending_moment=moment_kn_cm * KN_M_PER_KN_CM,
        bending_moment_position=position,
        d=depth,
    )
    calculator.calculate_for(STIRRUP_DIAMETER, 0.0, 0.0)
    return calculator.tensioned_rebar_area


def _assert_area(actual: float, expected: float, name: str) -> None:
    assert_approx(
        actual,
        expected,
        f"{name} should be {expected} cm2",
        abs_tol=TABLE_TOLERANCE * expected,
    )


class TestFlexuralReinforcement:
    """Items 19.7.3 to 19.7.6 — required area of each critical section"""

    def test_negative_moment_at_inner_support(self) -> None:
        _assert_area(_required_area(-11_507, 719.0, 55), 7.32, "As at P2")

    def test_negative_moment_at_stiffer_end_support(self) -> None:
        _assert_area(_required_area(-3_222, LENGTH, 57), 1.82, "As at P3")

    def test_negative_moment_at_softer_end_support_takes_minimum_area(self) -> None:
        """Item 19.7.5 a) — the required 0.66 cm2 is below the minimum"""
        assert_approx(
            _required_area(-1_171, 0.0, 57),
            MINIMUM_AREA,
            "As at P1 should be the minimum area, 1.71 cm2",
            abs_tol=TABLE_TOLERANCE * MINIMUM_AREA,
        )

    def test_positive_moment_in_first_span(self) -> None:
        _assert_area(_required_area(8_735, 282.6, 57), 5.15, "As of span 1")

    def test_positive_moment_in_second_span(self) -> None:
        _assert_area(_required_area(7_328, 1142.0, 57), 4.32, "As of span 2")
