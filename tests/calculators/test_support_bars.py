"""Unit tests for src/calculators/support_bars.py."""

import types
from collections.abc import Sequence
from typing import cast

import pytest

from src.calculators.support_bars import (
    SpanRange,
    carry_span_bars_to_supports,
    support_area_share,
)
from src.errors import SupportBarsShortError
from src.properties.steel import Steel
from src.reinforcement.layer import Layer
from src.reinforcement.reinforcement import Reinforcement
from src.structural_elements.rebar import Rebar
from tests.helpers import assert_approx

_SPAN = SpanRange(0.0, 500.0, 0, 1)
_SPAN_MOMENT = 50.0  # kN.m


def _layer(index: int, count: int, diameter_mm: float = 10.0) -> Layer:
    """Build a layer of equal bars (a 10 mm bar is 0.785 cm²)."""
    return Layer(
        [Rebar(diameter_mm=diameter_mm, steel=Steel.CA50) for _ in range(count)],
        index,
    )


class _ReinforcementDouble(types.SimpleNamespace):
    """Stand in for a Reinforcement, recording the layers extended into each support."""

    extended: list[tuple[int, int, bool]]
    reaching: set[tuple[int, int, bool]]
    support_moments: tuple[float, ...]

    def support_moment(self, support_index: int) -> float:
        return self.support_moments[support_index]

    def layer_reaches_support(
        self, layer_index: int, support_index: int, left: bool
    ) -> bool:
        return (layer_index, support_index, left) in self.reaching

    def extend_layer_to_support(
        self, layer_index: int, support_index: int, left: bool
    ) -> None:
        self.extended.append((layer_index, support_index, left))
        self.reaching.add((layer_index, support_index, left))


def _reinforcement(
    layers: Sequence[Layer],
    required_area: float,
    *,
    support_moments: tuple[float, float] = (0.0, 0.0),
    span_moment: float | None = _SPAN_MOMENT,
    center: float = 250.0,
    is_bottom: bool = True,
    reaching: set[tuple[int, int, bool]] | None = None,
) -> _ReinforcementDouble:
    """Build a reinforcement double over the 500 cm span, with up to three layers."""
    chosen = list(layers) + [_layer(i, 0) for i in range(len(layers), 3)]
    return _ReinforcementDouble(
        chosen_bars=chosen,
        required_area=required_area,
        span_moment=span_moment,
        support_moments=support_moments,
        center_position=center,
        is_bottom_reinforcement=is_bottom,
        is_tensioned=True,
        extended=[],
        reaching=reaching if reaching is not None else set(),
    )


def _run(*reinforcements: _ReinforcementDouble) -> None:
    carry_span_bars_to_supports(
        cast(list[Reinforcement], list(reinforcements)), [_SPAN]
    )


class TestSupportAreaShare:
    """1/3 or 1/4 of A_s,vão, with M_vão = 50 kN.m (NBR 6118 - 18.3.2.4-c)."""

    @pytest.mark.parametrize(
        ("support_moment", "share"),
        [
            (0.0, 1 / 3),  # null → 1/3
            (-25.0, 1 / 3),  # |M| = 0.5 M_vão → 1/3
            (-30.0, 1 / 4),  # |M| > 0.5 M_vão → 1/4
        ],
    )
    def test_share(self, support_moment: float, share: float) -> None:
        assert_approx(
            support_area_share(support_moment, _SPAN_MOMENT),
            share,
            "share of the span's area",
        )


class TestCarrySpanBarsToSupports:
    """Layers are extended in order, only until each support's share is met."""

    def test_first_layer_is_enough(self) -> None:
        """Layer 0 (2φ10 = 1.571 cm²) covers 1/3 of 4.0 cm² at both supports"""
        reinforcement = _reinforcement([_layer(0, 2), _layer(1, 2)], 4.0)
        _run(reinforcement)
        assert reinforcement.extended == [(0, 0, True), (0, 1, False)], (
            "only layer 0 is extended, into both supports"
        )

    def test_second_layer_when_first_is_short(self) -> None:
        """Layer 0 (1φ10 = 0.785 cm²) is below 1/3 of 4.0 cm² = 1.333 cm²"""
        reinforcement = _reinforcement([_layer(0, 1), _layer(1, 2)], 4.0)
        _run(reinforcement)
        assert reinforcement.extended == [
            (0, 0, True),
            (1, 0, True),
            (0, 1, False),
            (1, 1, False),
        ], "layers 0 and 1 are extended into each support"

    def test_quarter_share_with_large_negative_support_moment(self) -> None:
        """1/4 of 4.0 cm² = 1.0 cm²: layer 0 (0.785 cm²) alone is short"""
        reinforcement = _reinforcement(
            [_layer(0, 1), _layer(1, 2)],
            4.0,
            support_moments=(0.0, -30.0),
        )
        _run(reinforcement)
        assert (1, 1, False) in reinforcement.extended, (
            "layer 1 also goes into the right support"
        )

    def test_quarter_share_met_by_first_layer(self) -> None:
        """1/4 of 3.0 cm² = 0.75 cm² ≤ 0.785 cm², but 1/3 = 1.0 cm² is not"""
        reinforcement = _reinforcement(
            [_layer(0, 1), _layer(1, 2)],
            3.0,
            support_moments=(0.0, -30.0),
        )
        _run(reinforcement)
        assert reinforcement.extended == [(0, 0, True), (1, 0, True), (0, 1, False)], (
            "the right support (1/4) only needs layer 0; the left (1/3) needs both"
        )

    def test_positive_support_moment_is_skipped(self) -> None:
        """M_apoio > 0 on the right support: its bars come from the section's design"""
        reinforcement = _reinforcement(
            [_layer(0, 1), _layer(1, 2)], 4.0, support_moments=(0.0, 10.0)
        )
        _run(reinforcement)
        assert reinforcement.extended == [(0, 0, True), (1, 0, True)], (
            "only the left support (null moment) gets extended layers"
        )

    def test_numerically_null_support_moment_is_checked(self) -> None:
        """A support moment within the tolerance reads as null (1/3)"""
        reinforcement = _reinforcement(
            [_layer(0, 2)], 4.0, support_moments=(1e-6, 1e-6)
        )
        _run(reinforcement)
        assert reinforcement.extended == [(0, 0, True), (0, 1, False)], (
            "a null moment still carries the bars to both supports"
        )

    def test_reaching_layers_count(self) -> None:
        """Layer 1 already reaches both supports and covers the share alone"""
        reaching = {(1, 0, True), (1, 1, False)}
        reinforcement = _reinforcement(
            [_layer(0, 2), _layer(1, 2)], 4.0, reaching=reaching
        )
        _run(reinforcement)
        assert reinforcement.extended == [], "nothing is extended"

    def test_reaching_layer_is_skipped(self) -> None:
        """Layer 0 already reaches but is short; layer 1 is extended"""
        reinforcement = _reinforcement(
            [_layer(0, 1), _layer(1, 2)], 4.0, reaching={(0, 0, True), (0, 1, False)}
        )
        _run(reinforcement)
        assert reinforcement.extended == [(1, 0, True), (1, 1, False)], (
            "only the layer that does not reach is extended"
        )

    def test_negative_moment_bars_are_skipped(self) -> None:
        reinforcement = _reinforcement([_layer(0, 1)], 4.0, span_moment=None)
        _run(reinforcement)
        assert reinforcement.extended == [], "only positive-moment bars are checked"

    def test_top_bars_are_skipped(self) -> None:
        reinforcement = _reinforcement([_layer(0, 1)], 4.0, is_bottom=False)
        _run(reinforcement)
        assert reinforcement.extended == [], "only bottom bars are checked"

    def test_other_span_is_skipped(self) -> None:
        reinforcement = _reinforcement([_layer(0, 1)], 4.0, center=750.0)
        _run(reinforcement)
        assert reinforcement.extended == [], "bars outside the span are not checked"

    def test_greatest_span_moment_governs(self) -> None:
        smaller = _reinforcement([_layer(0, 1)], 4.0, span_moment=20.0, center=100.0)
        greater = _reinforcement([_layer(0, 2)], 4.0, span_moment=50.0, center=300.0)
        _run(smaller, greater)
        assert smaller.extended == [], "the smaller span moment is not M_vão"
        assert greater.extended == [(0, 0, True), (0, 1, False)], (
            "the greatest span moment's bars are carried"
        )

    def test_share_not_met_raises(self) -> None:
        """All layers (0.785 cm²) are below 1/3 of 6.0 cm² = 2.0 cm²"""
        reinforcement = _reinforcement([_layer(0, 1)], 6.0)
        with pytest.raises(SupportBarsShortError, match="below"):
            _run(reinforcement)
