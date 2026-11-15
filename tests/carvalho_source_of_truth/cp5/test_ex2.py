"""Carvalho, chapter 5, Example 2 — anchorage of a 12.5 mm bar with an end hook.

FROZEN: inputs and expected values come from the book's worked example
(Carvalho & Figueiredo Filho, 2014).
Do not change them; see the "Source-of-truth tests" section of AGENTS.md.
"""

import pytest

from src.calculators.anchorage_calculator import AnchorageCalculator
from src.config import APP_CONFIG
from src.properties.concrete import Concrete
from src.properties.steel import Steel
from src.reinforcement.reinforcement import Reinforcement
from src.structural_elements.rebar import Rebar
from src.structural_elements.rectangular_beam import RectangularBeam
from tests.carvalho_source_of_truth.book_tolerance import assert_book_value


@pytest.fixture(autouse=True)
def book_concrete(monkeypatch: pytest.MonkeyPatch) -> None:
    """Set the concrete of the example (C20)"""
    monkeypatch.setattr(APP_CONFIG, "pavement_concrete", Concrete.C20)


@pytest.fixture
def calculator() -> AnchorageCalculator:
    """Calculator for one hooked 12.5 mm CA-50 bar in a good-adherence zone

    The book gives no beam; a 40 cm high one keeps the bar in the good zone.
    """
    beam = RectangularBeam(length=500, width=18, height=40, steel=Steel.CA50)
    reinforcement = Reinforcement(
        beam, is_bottom_reinforcement=True, center_position=250
    )
    layer = reinforcement.chosen_bars[0]
    layer.bars = [Rebar(12.5, Steel.CA50)]
    layer.y_centroid_position = 4.0  # cm from the bottom face
    layer.set_hooks(left=True, enable=True)
    reinforcement.required_area = reinforcement.area
    calculator = AnchorageCalculator(
        moment_shift=0, steel=Steel.CA50, layer_index=0, reinforcement=reinforcement
    )
    calculator.left = True
    return calculator


class TestCarvalhoCp5Example2:
    """Expected results of Example 2"""

    def test_anchorage_length_with_hook(self, calculator: AnchorageCalculator) -> None:
        assert_book_value(
            calculator.necessary_anchorage_length,
            38.26,
            "l_b with hook should be 38.26 cm",
            decimals=2,
        )

    # FIXME this test, after the hook length is implemented
    @pytest.mark.xfail(
        strict=True,
        raises=AttributeError,
        reason="engine does not compute the hook length yet",
    )
    def test_hook_length(self, calculator: AnchorageCalculator) -> None:
        hook_length: float = getattr(calculator, "hook_length")  # noqa: B009 — attribute does not exist yet; cm
        assert_book_value(hook_length, 16, "l_hook should be about 16 cm", decimals=0)
