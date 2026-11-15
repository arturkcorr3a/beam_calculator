"""Carvalho, chapter 4, Example 1 — cross-section detailing of beam V101.

The layouts are the book's: 12 bars of 12.5 mm in 4 layers at the support and
6 bars in 2 layers in the span, with 6.3 mm stirrups.

FROZEN: inputs and expected values come from the book's worked example
(Carvalho & Figueiredo Filho, 2014, p. 244–257).
Do not change them; see the "Source-of-truth tests" section of AGENTS.md.
"""

import pytest

from src.calculators.rebar_calculator import RebarCalculator
from src.config import APP_CONFIG
from src.config_options import ExposureClass
from src.properties.concrete import Concrete
from src.properties.steel import Steel
from src.reinforcement.reinforcement import Reinforcement
from src.structural_elements.rebar import Rebar
from src.structural_elements.rectangular_beam import RectangularBeam
from tests.carvalho_source_of_truth.book_tolerance import assert_book_value

BAR_DIAMETER = 1.25  # cm
STIRRUP_DIAMETER = 0.63  # cm
RIB_ALLOWANCE = 0.05  # cm, the book adds 0.04 phi to each bar for its ribs
HEIGHT = 95  # cm


@pytest.fixture(autouse=True)
def book_inputs(monkeypatch: pytest.MonkeyPatch) -> None:
    """Set the materials, environment and aggregate of the example

    C20, CAA I, brita 2 (d_max = 2.5 cm), and room for the book's 4 layers.
    """
    monkeypatch.setattr(APP_CONFIG, "pavement_concrete", Concrete.C20)
    monkeypatch.setattr(APP_CONFIG, "exposure_class", ExposureClass.WEAK)
    monkeypatch.setattr(APP_CONFIG, "max_aggregate_size", 2.5)
    monkeypatch.setattr(APP_CONFIG, "max_layers", 4)


@pytest.fixture
def beam() -> RectangularBeam:
    """V101 section, 18 x 95 cm, CA50, two 8.00 m spans"""
    return RectangularBeam(length=1600, width=18, height=HEIGHT, steel=Steel.CA50)


def _bars(count: int) -> list[Rebar]:
    """Return a number of 12.5 mm CA50 bars"""
    return [Rebar(BAR_DIAMETER * 10, Steel.CA50) for _ in range(count)]


def _layout(beam: RectangularBeam, *, is_bottom: bool, count: int) -> Reinforcement:
    """Place a number of 12.5 mm bars in layers, as chosen bars"""
    reinforcement = Reinforcement(
        beam, is_bottom_reinforcement=is_bottom, center_position=800
    )
    reinforcement.stirrup_diameter = STIRRUP_DIAMETER
    reinforcement.distribute_bars_in_layers(_bars(count))
    reinforcement.is_chosen = True
    return reinforcement


def _calculator_for(
    beam: RectangularBeam, reinforcement: Reinforcement, bending_moment: float
) -> RebarCalculator:
    """Calculator whose effective depth follows a given tensioned layout"""
    calculator = RebarCalculator(
        beam=beam,
        bending_moment=bending_moment,
        bending_moment_position=reinforcement.center_position,
    )
    calculator.tensioned_reinforcement = reinforcement
    calculator.stirrup_diameter = STIRRUP_DIAMETER
    return calculator


@pytest.fixture
def support_layout(beam: RectangularBeam) -> Reinforcement:
    """Figure 4.18b — 12 top bars at the support"""
    return _layout(beam, is_bottom=False, count=12)


@pytest.fixture
def span_layout(beam: RectangularBeam) -> Reinforcement:
    """Figure 4.18a — 6 bottom bars in the span"""
    return _layout(beam, is_bottom=True, count=6)


class TestSpacing:
    """Item i.1/i.2) — spacing between bars"""

    def test_horizontal_center_to_center(self, support_layout: Reinforcement) -> None:
        free = support_layout.get_horizontal_spacing(BAR_DIAMETER)
        center_to_center = free + BAR_DIAMETER + RIB_ALLOWANCE
        assert_book_value(center_to_center, 4.3, "a_h should be 4.3 cm", decimals=1)

    def test_three_bars_fit_in_a_layer(self, support_layout: Reinforcement) -> None:
        assert support_layout.check_for_enough_space(_bars(3)), (
            "3 bars should fit in a layer"
        )

    def test_four_bars_do_not_fit_in_a_layer(
        self, support_layout: Reinforcement
    ) -> None:
        assert not support_layout.check_for_enough_space(_bars(4)), (
            "4 bars should not fit in a layer"
        )

    def test_vertical_free_spacing(self) -> None:
        free = Reinforcement.get_vertical_spacing(BAR_DIAMETER)
        book_free = 3.3 - BAR_DIAMETER - RIB_ALLOWANCE  # book prints center to center
        assert_book_value(free, book_free, "free a_v should be 2.2 cm", decimals=1)


class TestSupportLayout:
    """Figure 4.18b and item i.3) — support section"""

    def test_bars_per_layer(self, support_layout: Reinforcement) -> None:
        counts = [len(layer.bars) for layer in support_layout.chosen_bars]
        assert counts == [3, 3, 3, 3], "support should have 4 layers of 3 bars"

    def test_provided_area(self, support_layout: Reinforcement) -> None:
        assert_book_value(
            support_layout.area, 14.72, "provided As should be 14.72 cm²", decimals=2
        )

    @pytest.mark.xfail(
        strict=True, reason="layer pitch is 3.5 cm in the book, 3.25 cm in the engine"
    )
    def test_centroid_distance(
        self, beam: RectangularBeam, support_layout: Reinforcement
    ) -> None:
        calculator = _calculator_for(beam, support_layout, -326.20)
        y_cg = HEIGHT - calculator.d  # cm, from the top
        assert_book_value(y_cg, 9.03, "y_cg should be 9.03 cm", decimals=2)

    def test_effective_depth(
        self, beam: RectangularBeam, support_layout: Reinforcement
    ) -> None:
        calculator = _calculator_for(beam, support_layout, -326.20)
        assert_book_value(calculator.d, 85.97, "d should be 85.97 cm", decimals=2)

    def test_effective_depth_above_adopted(
        self, beam: RectangularBeam, support_layout: Reinforcement
    ) -> None:
        calculator = _calculator_for(beam, support_layout, -326.20)
        assert calculator.d > 85, "d_real should exceed the adopted 85 cm"


class TestSpanLayout:
    """Figure 4.18a and item i.3) — span section"""

    def test_bars_per_layer(self, span_layout: Reinforcement) -> None:
        counts = [len(layer.bars) for layer in span_layout.chosen_bars]
        assert counts == [3, 3, 0, 0], "span should have 2 layers of 3 bars"

    def test_provided_area(self, span_layout: Reinforcement) -> None:
        assert_book_value(
            span_layout.area, 7.36, "provided As should be 7.36 cm²", decimals=2
        )

    def test_effective_depth(
        self, beam: RectangularBeam, span_layout: Reinforcement
    ) -> None:
        calculator = _calculator_for(beam, span_layout, 183.50)
        assert_book_value(calculator.d, 89.47, "d should be 89.47 cm", decimals=2)
