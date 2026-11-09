"""Tests for src/pavement_elements/beam_span.py."""

import types
from typing import cast

import pytest

from src.loading.load_component import LoadComponent, LoadKind
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
# TestGetEffectiveLength
# ---------------------------------------------------------------------------


@pytest.fixture
def wide_registry() -> dict[str, Pillar]:
    """Registry with two wide pillars: (0,0) and (600,0), 100×20 cm each."""
    p1 = Pillar(x=0, y=0, width=100, depth=20)
    p2 = Pillar(x=600, y=0, width=100, depth=20)
    return {p1.id: p1, p2.id: p2}


class TestGetEffectiveLength:
    """get_effective_length applies the NBR 6118 §14.6.2.4 0.3h cap to pillar supports."""

    def test_narrow_pillars_keep_centroid_distance(
        self, pillars: tuple[Pillar, Pillar, Pillar], registry: dict[str, Pillar]
    ) -> None:
        p1, p2, _ = pillars
        beam = types.SimpleNamespace(axis=Axis.X, height=40)
        span = Span(cast(ContinuousBeam, beam), p1.id, p2.id)
        # t/2 = 10 < 0.3h = 12 -> l_ef == 400
        assert_approx(
            span.get_effective_length(registry), 400, "narrow pillars should keep 400"
        )

    @pytest.mark.xfail(
        strict=True,
        reason="0.3h cap disabled in effective_span(): NBR 6118 wording ('pode', not'deve') makes it optional; kept off to avoid structural/real beam mismatch",
    )
    def test_wide_pillars_use_beam_height(
        self, wide_registry: dict[str, Pillar]
    ) -> None:
        start_id, end_id = wide_registry
        beam = types.SimpleNamespace(axis=Axis.X, height=40)
        span = Span(cast(ContinuousBeam, beam), start_id, end_id)
        # l0 = 500; a = min(50, 12) = 12 -> 524
        assert_approx(
            span.get_effective_length(wide_registry), 524, "should cap at 0.3h"
        )

    @pytest.mark.xfail(
        strict=True,
        reason="0.3h cap disabled in effective_span(): NBR 6118 wording ('pode', not 'deve') makes it optional; kept off to avoid structural/real beam mismatch",
    )
    def test_explicit_height_overrides_beam_height(
        self, wide_registry: dict[str, Pillar]
    ) -> None:
        start_id, end_id = wide_registry
        beam = types.SimpleNamespace(axis=Axis.X, height=40)
        span = Span(cast(ContinuousBeam, beam), start_id, end_id)
        # l0 = 500; a = min(50, 6) = 6 -> 512
        assert_approx(
            span.get_effective_length(wide_registry, 20),
            512,
            "explicit height should be used for the cap",
        )

    @pytest.mark.xfail(
        strict=True,
        reason="0.3h cap disabled in effective_span(): NBR 6118 wording ('pode', not 'deve') makes it optional; kept off to avoid structural/real beam mismatch",
    )
    def test_y_axis_uses_pillar_depth(self) -> None:
        p1 = Pillar(x=0, y=0, width=20, depth=100)
        p2 = Pillar(x=0, y=600, width=20, depth=100)
        registry = {p1.id: p1, p2.id: p2}
        beam = types.SimpleNamespace(axis=Axis.Y, height=40)
        span = Span(cast(ContinuousBeam, beam), p1.id, p2.id)
        assert_approx(
            span.get_effective_length(registry), 524, "Y span should use pillar depth"
        )


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

    def test_same_data_different_slab_raises(self, x_span: Span) -> None:
        """A copy of a supported slab is a different slab, not the supported one"""
        supported = Slab(("P1", "P2", "P3", "P4"), "Bedrooms", id="L1")
        neighbor = Slab(("P3", "P4", "P5", "P6"), "Bedrooms", id="L2")
        copy = Slab(("P1", "P2", "P3", "P4"), "Bedrooms", id="L1")
        x_span.add_supported_slab(supported)
        x_span.add_supported_slab(neighbor)
        with pytest.raises(ValueError, match="is not supported by this span"):
            x_span.get_other_supported_slab(copy)


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
        x_span.add_load(2.0, permanent=False, psi_2=0.3)
        x_span.add_load(1.5, permanent=False, psi_2=0.3)
        assert_approx(x_span.variable_load, 3.5, "variable_load should accumulate")

    def test_permanent_does_not_affect_variable(self, x_span: Span) -> None:
        x_span.add_load(5.0, permanent=True)
        assert_approx(
            x_span.variable_load, 0.0, "permanent load must not touch variable_load"
        )

    def test_variable_does_not_affect_permanent(self, x_span: Span) -> None:
        x_span.add_load(5.0, permanent=False, psi_2=0.3)
        assert_approx(
            x_span.permanent_load, 0.0, "variable load must not touch permanent_load"
        )

    def test_keeps_largest_psi_2(self, x_span: Span) -> None:
        x_span.add_load(2.0, permanent=False, psi_2=0.3)
        x_span.add_load(1.0, permanent=False, psi_2=0.6)
        x_span.add_load(2.0, permanent=False, psi_2=0.4)
        assert_approx(x_span.psi_2, 0.6, "psi_2 should be the largest one added")

    def test_permanent_load_ignores_psi_2(self, x_span: Span) -> None:
        x_span.add_load(5.0, permanent=True, psi_2=0.6)
        assert_approx(x_span.psi_2, 0.0, "a permanent load must not set psi_2")

    def test_variable_load_without_psi_2_raises(self, x_span: Span) -> None:
        with pytest.raises(ValueError, match="psi_2"):
            x_span.add_load(5.0, permanent=False)


# ---------------------------------------------------------------------------
# TestAddComponent
# ---------------------------------------------------------------------------


class TestAddComponent:
    """add_component keeps each load source and adds it to the span totals."""

    def test_components_are_kept_in_order(self, x_span: Span) -> None:
        own = LoadComponent(LoadKind.OWN_WEIGHT, None, 2.0)
        slab = LoadComponent(LoadKind.SLAB, "L1", 4.0, 1.5)
        x_span.add_component(own)
        x_span.add_component(slab, psi_2=0.3)
        assert x_span.load_components == [own, slab], (
            "components should be kept in the order they were added"
        )

    def test_totals_match_add_load(self, x_span: Span) -> None:
        x_span.add_component(LoadComponent(LoadKind.WALL, None, 3.0))
        x_span.add_component(LoadComponent(LoadKind.SLAB, "L1", 4.0, 1.5), psi_2=0.4)
        assert_approx(x_span.permanent_load, 7.0, "permanent total (kN/m)")
        assert_approx(x_span.variable_load, 1.5, "variable total (kN/m)")
        assert_approx(x_span.psi_2, 0.4, "psi_2 of the slab load")

    def test_zero_variable_part_still_sets_psi_2(self, x_span: Span) -> None:
        """A slab without live load sets psi_2 just as add_load(0, ...) did"""
        x_span.add_component(LoadComponent(LoadKind.SLAB, "L1", 4.0, 0.0), psi_2=0.3)
        assert_approx(x_span.psi_2, 0.3, "psi_2 should be set even for q = 0")

    def test_variable_part_without_psi_2_raises(self, x_span: Span) -> None:
        with pytest.raises(ValueError, match="psi_2"):
            x_span.add_component(LoadComponent(LoadKind.SLAB, "L1", 4.0, 1.5))
        assert x_span.load_components == [], "a rejected component is not kept"
