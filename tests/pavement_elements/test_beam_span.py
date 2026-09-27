"""Tests for src/pavement_elements/beam_span.py."""

import types
from typing import cast

import pytest

from src.pavement_elements.beam_span import Span
from src.pavement_elements.continuous_beam import ContinuousBeam
from src.pavement_elements.geometry_utils import Axis
from src.pavement_elements.pillar import Pillar
from src.pavement_elements.slab import Slab
from tests.helpers import assert_approx

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def pillars() -> tuple[Pillar, Pillar, Pillar]:
    """Three pillars: p1(0,0), p2(400,0), p3(0,300)."""
    p1 = Pillar(x=0, y=0, width=20, depth=20)
    p2 = Pillar(x=400, y=0, width=20, depth=20)
    p3 = Pillar(x=0, y=300, width=20, depth=20)
    return p1, p2, p3


@pytest.fixture
def registry(pillars: tuple[Pillar, Pillar, Pillar]) -> dict[str, Pillar]:
    """Pillar registry containing all three fixture pillars."""
    p1, p2, p3 = pillars
    return {p1.id: p1, p2.id: p2, p3.id: p3}


@pytest.fixture
def x_span(pillars: tuple[Pillar, Pillar, Pillar]) -> Span:
    """Horizontal Span between p1 and p2 (Axis.X)."""
    p1, p2, _ = pillars
    beam = types.SimpleNamespace(axis=Axis.X)
    return Span(cast(ContinuousBeam, beam), p1.id, p2.id)


@pytest.fixture
def y_span(pillars: tuple[Pillar, Pillar, Pillar]) -> Span:
    """Vertical Span between p1 and p3 (Axis.Y)."""
    p1, _, p3 = pillars
    beam = types.SimpleNamespace(axis=Axis.Y)
    return Span(cast(ContinuousBeam, beam), p1.id, p3.id)


@pytest.fixture
def slab_a() -> Slab:
    """Slab double with id='LA', thickness=10."""
    return cast(Slab, types.SimpleNamespace(id="LA", thickness=10))


@pytest.fixture
def slab_b() -> Slab:
    """Slab double with id='LB', thickness=12."""
    return cast(Slab, types.SimpleNamespace(id="LB", thickness=12))


# ---------------------------------------------------------------------------
# TestInitialDefaults
# ---------------------------------------------------------------------------


class TestInitialDefaults:
    """Span fields default to zero / None at construction (init=False)."""

    def test_permanent_load_defaults_to_zero(self, x_span: Span) -> None:
        assert_approx(x_span.permanent_load, 0.0, "permanent_load should default to 0")

    def test_variable_load_defaults_to_zero(self, x_span: Span) -> None:
        assert_approx(x_span.variable_load, 0.0, "variable_load should default to 0")

    def test_supported_slabs_defaults_to_none_none(self, x_span: Span) -> None:
        assert x_span.supported_slabs == (None, None), (
            "supported_slabs should default to (None, None)"
        )


# ---------------------------------------------------------------------------
# TestGetLength
# ---------------------------------------------------------------------------


class TestGetLength:
    """get_length dispatches on the beam axis."""

    def test_x_axis_returns_horizontal_distance(
        self, x_span: Span, registry: dict[str, Pillar]
    ) -> None:
        assert_approx(x_span.get_length(registry), 400, "X span length should be 400")

    def test_y_axis_returns_vertical_distance(
        self, y_span: Span, registry: dict[str, Pillar]
    ) -> None:
        assert_approx(y_span.get_length(registry), 300, "Y span length should be 300")

    def test_none_axis_raises(
        self, pillars: tuple[Pillar, Pillar, Pillar], registry: dict[str, Pillar]
    ) -> None:
        p1, p2, _ = pillars
        beam = types.SimpleNamespace(axis=None)
        span = Span(cast(ContinuousBeam, beam), p1.id, p2.id)
        with pytest.raises(ValueError, match="Invalid axis for length calculation"):
            span.get_length(registry)


# ---------------------------------------------------------------------------
# TestContainsPillar
# ---------------------------------------------------------------------------


class TestContainsPillar:
    """contains_pillar checks the start and end pillar ids."""

    def test_start_pillar_is_contained(
        self, x_span: Span, pillars: tuple[Pillar, Pillar, Pillar]
    ) -> None:
        p1, _, _ = pillars
        assert x_span.contains_pillar(p1.id), "start pillar should be contained"

    def test_end_pillar_is_contained(
        self, x_span: Span, pillars: tuple[Pillar, Pillar, Pillar]
    ) -> None:
        _, p2, _ = pillars
        assert x_span.contains_pillar(p2.id), "end pillar should be contained"

    def test_unrelated_pillar_is_not_contained(
        self, x_span: Span, pillars: tuple[Pillar, Pillar, Pillar]
    ) -> None:
        _, _, p3 = pillars
        assert not x_span.contains_pillar(p3.id), (
            "unrelated pillar should not be contained"
        )


# ---------------------------------------------------------------------------
# TestAddSupportedSlab
# ---------------------------------------------------------------------------


class TestAddSupportedSlab:
    """add_supported_slab fills the two slots; a third raises."""

    def test_fills_first_slot(self, x_span: Span, slab_a: Slab) -> None:
        x_span.add_supported_slab(slab_a)
        assert x_span.supported_slabs[0] is slab_a, "first slab should be in slot 0"

    def test_fills_second_slot(self, x_span: Span, slab_a: Slab, slab_b: Slab) -> None:
        x_span.add_supported_slab(slab_a)
        x_span.add_supported_slab(slab_b)
        assert x_span.supported_slabs[1] is slab_b, "second slab should be in slot 1"

    def test_third_slab_raises(self, x_span: Span, slab_a: Slab, slab_b: Slab) -> None:
        slab_c = cast(Slab, types.SimpleNamespace(id="LC", thickness=14))
        x_span.add_supported_slab(slab_a)
        x_span.add_supported_slab(slab_b)
        with pytest.raises(ValueError, match="already supports two slabs"):
            x_span.add_supported_slab(slab_c)


# ---------------------------------------------------------------------------
# TestGetOtherSupportedSlab
# ---------------------------------------------------------------------------


class TestGetOtherSupportedSlab:
    """get_other_supported_slab returns the slab in the other slot."""

    def test_returns_slab_b_when_querying_slab_a(
        self, x_span: Span, slab_a: Slab, slab_b: Slab
    ) -> None:
        x_span.add_supported_slab(slab_a)
        x_span.add_supported_slab(slab_b)
        other = x_span.get_other_supported_slab(slab_a)
        assert other is slab_b, "querying slot-0 slab should return slot-1 slab"

    def test_returns_slab_a_when_querying_slab_b(
        self, x_span: Span, slab_a: Slab, slab_b: Slab
    ) -> None:
        x_span.add_supported_slab(slab_a)
        x_span.add_supported_slab(slab_b)
        other = x_span.get_other_supported_slab(slab_b)
        assert other is slab_a, "querying slot-1 slab should return slot-0 slab"

    def test_unknown_slab_raises(
        self, x_span: Span, slab_a: Slab, slab_b: Slab
    ) -> None:
        x_span.add_supported_slab(slab_a)
        x_span.add_supported_slab(slab_b)
        unknown = cast(Slab, types.SimpleNamespace(id="L99", thickness=10))
        with pytest.raises(ValueError, match="is not supported by this span"):
            x_span.get_other_supported_slab(unknown)


# ---------------------------------------------------------------------------
# TestAddLoad
# ---------------------------------------------------------------------------


class TestAddLoad:
    """add_load accumulates loads into the correct fields."""

    def test_permanent_load_accumulates(self, x_span: Span) -> None:
        x_span.add_load(5.0, permanent=True)
        x_span.add_load(3.0, permanent=True)
        assert_approx(x_span.permanent_load, 8.0, "permanent_load should accumulate")

    def test_variable_load_accumulates(self, x_span: Span) -> None:
        x_span.add_load(2.0, permanent=False)
        x_span.add_load(1.5, permanent=False)
        assert_approx(x_span.variable_load, 3.5, "variable_load should accumulate")

    def test_permanent_does_not_affect_variable(self, x_span: Span) -> None:
        x_span.add_load(5.0, permanent=True)
        assert_approx(
            x_span.variable_load, 0.0, "permanent load must not touch variable_load"
        )

    def test_variable_does_not_affect_permanent(self, x_span: Span) -> None:
        x_span.add_load(5.0, permanent=False)
        assert_approx(
            x_span.permanent_load, 0.0, "variable load must not touch permanent_load"
        )
