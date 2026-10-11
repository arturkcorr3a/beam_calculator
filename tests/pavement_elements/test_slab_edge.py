"""Tests for src/pavement_elements/slab_edge.py."""

import types
from typing import cast

import pytest

from src.pavement_elements.beam_span import Span
from src.pavement_elements.continuous_beam import ContinuousBeam
from src.pavement_elements.geometry_utils import Axis
from src.pavement_elements.pillar import Pillar
from src.pavement_elements.slab import Slab
from src.pavement_elements.slab_edge import (
    Edges,
    SlabEdge,
)
from tests.helpers import assert_approx

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def slab_double() -> Slab:
    """Minimal slab double (finishes 4 + own weight 2.5 kN/m², variable_load=2 kN/m²)."""
    return cast(
        Slab,
        types.SimpleNamespace(
            id="L_edge_test",
            thickness=10,
            permanent_load=4.0,
            total_permanent_load=6.5,
            variable_load=2.0,
            is_lowered=False,
        ),
    )


@pytest.fixture
def beam_double() -> ContinuousBeam:
    """Minimal beam double exposing only an id."""
    return cast(ContinuousBeam, types.SimpleNamespace(id="V_edge_test"))


@pytest.fixture
def bottom_edge(slab_double: Slab) -> SlabEdge:
    """Unresolved BOTTOM edge for slab_double."""
    return SlabEdge(Edges.BOTTOM, slab_double)


@pytest.fixture
def pillars() -> tuple[Pillar, Pillar]:
    """Two pillars 500 cm apart horizontally."""
    p1 = Pillar(x=0, y=0, width=20, depth=20)
    p2 = Pillar(x=500, y=0, width=20, depth=20)
    return p1, p2


@pytest.fixture
def pillar_registry(pillars: tuple[Pillar, Pillar]) -> dict[str, Pillar]:
    """Registry of the two fixture pillars."""
    p1, p2 = pillars
    return {p1.id: p1, p2.id: p2}


def _make_span(p1: Pillar, p2: Pillar, axis: Axis = Axis.X) -> Span:
    """Build a Span with the given axis between two pillars."""
    beam = cast(ContinuousBeam, types.SimpleNamespace(axis=axis))
    return Span(beam, p1.id, p2.id)


# ---------------------------------------------------------------------------
# TestLabel
# ---------------------------------------------------------------------------


class TestLabel:
    """label returns the slab's id."""

    def test_label_equals_slab_id(
        self, bottom_edge: SlabEdge, slab_double: Slab
    ) -> None:
        assert bottom_edge.label == slab_double.id, "label should equal slab.id"  # type: ignore[attr-defined]


# ---------------------------------------------------------------------------
# TestBeamProperty
# ---------------------------------------------------------------------------


class TestBeamProperty:
    """beam property raises before resolution, returns the beam after."""

    def test_unresolved_raises(self, bottom_edge: SlabEdge) -> None:
        with pytest.raises(ValueError, match="has no resolved supporting beam"):
            _ = bottom_edge.beam

    def test_unresolved_message_uses_edge_value(self, bottom_edge: SlabEdge) -> None:
        with pytest.raises(ValueError, match=r"^Slab edge 'bottom' has no"):
            _ = bottom_edge.beam

    def test_resolved_returns_beam(
        self, bottom_edge: SlabEdge, beam_double: ContinuousBeam
    ) -> None:
        bottom_edge.resolve_beam(beam_double)
        assert bottom_edge.beam is beam_double, "beam should return the resolved beam"


# ---------------------------------------------------------------------------
# TestClearResolved
# ---------------------------------------------------------------------------


class TestClearResolved:
    """clear_resolved resets the edge to its unresolved initial state."""

    def test_clears_beam_spans_and_condition(
        self,
        bottom_edge: SlabEdge,
        beam_double: ContinuousBeam,
        pillars: tuple[Pillar, Pillar],
    ) -> None:
        p1, p2 = pillars
        bottom_edge.resolve_beam(beam_double)
        bottom_edge.spans = [_make_span(p1, p2)]
        bottom_edge.support_condition = "fixed"

        bottom_edge.clear_resolved()

        assert bottom_edge._beam is None, "beam should be cleared"  # pyright: ignore[reportPrivateUsage]
        assert bottom_edge.spans == [], "spans should be cleared"
        assert bottom_edge.support_condition == "pinned", (
            "support_condition should reset to 'pinned'"
        )


# ---------------------------------------------------------------------------
# TestResolveSupportCondition
# ---------------------------------------------------------------------------


class TestResolveSupportCondition:
    """resolve_support_condition sets 'fixed' only when fixed_length/total > 0.8."""

    def test_empty_spans_raises_value_error(
        self, bottom_edge: SlabEdge, pillar_registry: dict[str, Pillar]
    ) -> None:
        """An edge without spans fails with a clear message, not a ZeroDivisionError"""
        with pytest.raises(ValueError, match=r"bottom edge has no supporting spans"):
            bottom_edge.resolve_support_condition(pillar_registry)

    def test_all_spans_no_other_slab_stays_pinned(
        self,
        slab_double: Slab,
        pillar_registry: dict[str, Pillar],
        pillars: tuple[Pillar, Pillar],
    ) -> None:
        """Span's other slot is None → supported_length only → stays pinned."""
        p1, p2 = pillars
        edge = SlabEdge(Edges.BOTTOM, slab_double)

        span = _make_span(p1, p2)
        # slab_double in slot-0, slot-1 is None → get_other_supported_slab returns None
        span.add_supported_slab(slab_double)
        edge.spans = [span]

        edge.resolve_support_condition(pillar_registry)
        assert edge.support_condition == "pinned", "no adjacent slab should stay pinned"

    def test_all_spans_similar_thickness_becomes_fixed(
        self,
        slab_double: Slab,
        pillar_registry: dict[str, Pillar],
        pillars: tuple[Pillar, Pillar],
    ) -> None:
        """Adjacent slab with equal thickness → within tolerance → all fixed."""
        p1, p2 = pillars
        edge = SlabEdge(Edges.BOTTOM, slab_double)
        # other_slab has same thickness as slab_double (10 cm) → |diff|=0 ≤ 2 → fixed
        other = cast(
            Slab, types.SimpleNamespace(id="L_adj", thickness=10, is_lowered=False)
        )

        span = _make_span(p1, p2)
        span.add_supported_slab(slab_double)
        span.add_supported_slab(other)
        edge.spans = [span]

        edge.resolve_support_condition(pillar_registry)
        assert edge.support_condition == "fixed", (
            "similar-thickness adjacent slab should produce fixed condition"
        )

    def test_adjacent_much_thinner_slab_stays_pinned(
        self,
        slab_double: Slab,
        pillar_registry: dict[str, Pillar],
        pillars: tuple[Pillar, Pillar],
    ) -> None:
        """Adjacent slab much thinner (diff > 2 cm and not > self) → supported."""
        p1, p2 = pillars
        edge = SlabEdge(Edges.BOTTOM, slab_double)
        # other.thickness = 5 cm < slab_double.thickness=10; diff=5 > 2 → supported_length
        other = cast(
            Slab, types.SimpleNamespace(id="L_thin", thickness=5, is_lowered=False)
        )

        span = _make_span(p1, p2)
        span.add_supported_slab(slab_double)
        span.add_supported_slab(other)
        edge.spans = [span]

        edge.resolve_support_condition(pillar_registry)
        assert edge.support_condition == "pinned", (
            "much-thinner adjacent slab should stay pinned"
        )

    def test_lowered_slab_stays_pinned(
        self, pillar_registry: dict[str, Pillar], pillars: tuple[Pillar, Pillar]
    ) -> None:
        """A lowered slab is never fixed, even next to an equal-thickness slab."""
        p1, p2 = pillars
        lowered = cast(
            Slab, types.SimpleNamespace(id="L_low", thickness=10, is_lowered=True)
        )
        other = cast(
            Slab, types.SimpleNamespace(id="L_adj", thickness=10, is_lowered=False)
        )
        edge = SlabEdge(Edges.BOTTOM, lowered)

        span = _make_span(p1, p2)
        span.add_supported_slab(lowered)
        span.add_supported_slab(other)
        edge.spans = [span]

        edge.resolve_support_condition(pillar_registry)
        assert edge.support_condition == "pinned", "lowered slab should stay pinned"

    def test_adjacent_lowered_slab_counts_as_no_slab(
        self,
        slab_double: Slab,
        pillar_registry: dict[str, Pillar],
        pillars: tuple[Pillar, Pillar],
    ) -> None:
        """A lowered neighbour of equal thickness does not fix the edge."""
        p1, p2 = pillars
        edge = SlabEdge(Edges.BOTTOM, slab_double)
        other = cast(
            Slab, types.SimpleNamespace(id="L_low", thickness=10, is_lowered=True)
        )

        span = _make_span(p1, p2)
        span.add_supported_slab(slab_double)
        span.add_supported_slab(other)
        edge.spans = [span]

        edge.resolve_support_condition(pillar_registry)
        assert edge.support_condition == "pinned", (
            "edge next to a lowered slab should stay pinned"
        )

    def test_re_resolving_resets_previous_fixed(
        self,
        slab_double: Slab,
        pillar_registry: dict[str, Pillar],
        pillars: tuple[Pillar, Pillar],
    ) -> None:
        """A second call recomputes from scratch instead of keeping 'fixed'."""
        p1, p2 = pillars
        edge = SlabEdge(Edges.BOTTOM, slab_double)
        other = types.SimpleNamespace(id="L_adj", thickness=10, is_lowered=False)

        span = _make_span(p1, p2)
        span.add_supported_slab(slab_double)
        span.add_supported_slab(cast(Slab, other))
        edge.spans = [span]

        edge.resolve_support_condition(pillar_registry)
        assert edge.support_condition == "fixed", "first call should fix the edge"

        other.thickness = 5
        edge.resolve_support_condition(pillar_registry)
        assert edge.support_condition == "pinned", (
            "second call should reset to pinned once the neighbour got much thinner"
        )


# ---------------------------------------------------------------------------
# TestUnloadOnSpans
# ---------------------------------------------------------------------------


class TestUnloadOnSpans:
    """unload_on_spans distributes slab loads as kN/m onto each span."""

    def test_distributes_expected_loads(
        self,
        slab_double: Slab,
        beam_double: ContinuousBeam,
        pillar_registry: dict[str, Pillar],
        pillars: tuple[Pillar, Pillar],
    ) -> None:
        """slab perm=6.5 kN/m² (with own weight), var=2 kN/m²; area=6.25 m²; edge_len=5 m → 8.125/2.5 kN/m."""
        p1, p2 = pillars
        edge = SlabEdge(Edges.BOTTOM, slab_double)
        edge.resolve_beam(beam_double)
        edge.influence_area = 6.25  # m²

        span = _make_span(p1, p2)
        edge.spans = [span]

        edge.unload_on_spans(pillar_registry)

        # permanent = (4.0 + 2.5 own weight) * 6.25 / 5.0 = 8.125 kN/m
        assert_approx(
            span.permanent_load,
            8.125,
            "permanent load should include the slab own weight (8.125 kN/m)",
        )
        # variable = 2.0 * 6.25 / 5.0 = 2.5 kN/m
        assert_approx(span.variable_load, 2.5, "variable load should be 2.5 kN/m")

    def test_empty_spans_raises_value_error(
        self, bottom_edge: SlabEdge, pillar_registry: dict[str, Pillar]
    ) -> None:
        """An edge without spans fails with a clear message, not a ZeroDivisionError"""
        bottom_edge.influence_area = 6.25  # m²
        with pytest.raises(ValueError, match=r"bottom edge has no supporting spans"):
            bottom_edge.unload_on_spans(pillar_registry)
