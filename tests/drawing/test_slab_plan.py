"""Tests for the slab drawings of the design report (src/drawing/slab_plan.py)."""

from unittest.mock import Mock

import pytest

from src.drawing.formatting import fmt_dec, fmt_len
from src.drawing.layers import (
    BEAM_OUTLINE,
    DIMENSION,
    PILLAR,
    SLAB_OUTLINE,
    SLAB_SUPPORT,
    TEXT,
    YIELD_LINE,
)
from src.drawing.primitives import Drawing, Line, Polyline, Text
from src.drawing.slab_plan import build_slab_plan, build_slab_supports
from src.pavement_elements.continuous_beam import ContinuousBeam
from src.pavement_elements.pavement import Pavement
from src.pavement_elements.slab import CORNER_EDGE_DICT, Slab
from src.pavement_elements.slab_edge import Edges, SupportCondition
from tests.helpers import centroid_preserving_beam_width

_BEAM_IDS = {Edges.BOTTOM: "VB", Edges.TOP: "VT", Edges.LEFT: "VL", Edges.RIGHT: "VR"}


def _slab(
    lx_cm: float, ly_cm: float, conditions: dict[Edges, SupportCondition]
) -> Slab:
    """Build a slab on mock beams, with its influence areas resolved"""
    slab = Slab(("P1", "P2", "P3", "P4"), "Bedrooms")
    for edge, centerline in (
        (Edges.LEFT, 0.0),
        (Edges.RIGHT, lx_cm),
        (Edges.BOTTOM, 0.0),
        (Edges.TOP, ly_cm),
    ):
        beam = Mock(spec=ContinuousBeam)
        beam.id = _BEAM_IDS[edge]
        beam.centerline = centerline
        beam.width = centroid_preserving_beam_width(slab.thickness)
        slab.edges[edge].resolve_beam(beam)
        slab.edges[edge].support_condition = conditions[edge]
    slab.resolve_influence_areas()
    return slab


def _all(
    condition: SupportCondition, **others: SupportCondition
) -> dict[Edges, SupportCondition]:
    """Return one condition for every edge, except the ones named by edge value"""
    return {edge: others.get(edge.value, condition) for edge in Edges}


def _texts(drawing: Drawing, layer: str = TEXT) -> list[str]:
    return [
        item.text
        for item in drawing.items
        if isinstance(item, Text) and item.layer == layer
    ]


def _lines(drawing: Drawing, layer: str) -> list[Line]:
    return [
        item for item in drawing.items if isinstance(item, Line) and item.layer == layer
    ]


class TestSupports:
    """Support symbols, yield lines and region labels"""

    def test_pinned_edges_are_plain_lines(self) -> None:
        drawing = build_slab_supports(_slab(500, 500, _all("pinned")))
        assert len(_lines(drawing, SLAB_SUPPORT)) == 4, "one line per edge, no hatch"

    def test_fixed_edge_is_hatched(self) -> None:
        conditions = _all("pinned", bottom="fixed")
        drawing = build_slab_supports(_slab(500, 500, conditions))
        ticks = [
            line
            for line in _lines(drawing, SLAB_SUPPORT)
            if line.start[1] == 0.0 and line.end[1] < 0.0
        ]
        assert len(ticks) > 4, "the bottom edge should be hatched below the slab"
        assert len(_lines(drawing, SLAB_SUPPORT)) == 4 + len(ticks), (
            "only the fixed edge gets ticks"
        )

    @pytest.mark.parametrize(
        "lx_cm,ly_cm,expected",
        [(500, 500, 4), (750, 500, 5), (1250, 500, 1)],
        ids=["square_no_ridge", "rectangle_with_ridge", "one_way_split"],
    )
    def test_yield_line_count(self, lx_cm: float, ly_cm: float, expected: int) -> None:
        drawing = build_slab_supports(_slab(lx_cm, ly_cm, _all("pinned")))
        assert len(_lines(drawing, YIELD_LINE)) == expected

    def test_regions_are_labelled(self) -> None:
        slab = _slab(750, 500, _all("fixed", top="pinned"))
        texts = _texts(build_slab_supports(slab))
        for edge in Edges:
            area = fmt_dec(slab.edges[edge].influence_area, 2)
            assert _BEAM_IDS[edge] in texts, f"{edge.value} region names its beam"
            assert f"{area} m²" in texts, f"{edge.value} region shows its area"

    def test_one_way_short_edges_have_no_label(self) -> None:
        texts = _texts(build_slab_supports(_slab(1250, 500, _all("pinned"))))
        assert sorted(t for t in texts if t.startswith("V")) == ["VB", "VT"]

    def test_effective_dimensions(self) -> None:
        slab = _slab(750, 500, _all("pinned"))
        lx, ly = slab.effective_dimensions
        assert sorted(_texts(build_slab_supports(slab), DIMENSION)) == sorted(
            [f"lx,ef = {fmt_len(lx)}", f"ly,ef = {fmt_len(ly)}"]
        )


class TestPlan:
    """The plan of every slab of t_concreto2"""

    def test_beams_pillars_and_dimensions(self, t_concreto2: Pavement) -> None:
        for slab in t_concreto2.slabs.values():
            drawing = build_slab_plan(slab, t_concreto2.pillars)
            texts = _texts(drawing)
            for edge in Edges:
                assert slab.edges[edge].beam.id in texts, f"{slab.id}: {edge} beam"
                for key in CORNER_EDGE_DICT[edge]:
                    pillar = slab.corners_pillar_dict[key]
                    assert pillar.id in texts, f"{slab.id}: corner pillar named"
            assert slab.id in texts, "the slab is named"
            lx, ly = slab.dimensions
            assert sorted(_texts(drawing, DIMENSION)) == sorted(
                [f"lx = {fmt_len(lx)}", f"ly = {fmt_len(ly)}"]
            )

    def test_outlines(self, t_concreto2: Pavement) -> None:
        slab = next(iter(t_concreto2.slabs.values()))
        drawing = build_slab_plan(slab, t_concreto2.pillars)
        polylines = [item for item in drawing.items if isinstance(item, Polyline)]
        layers = [item.layer for item in polylines]
        assert layers.count(SLAB_OUTLINE) == 1, "one slab outline"
        assert layers.count(BEAM_OUTLINE) == 4, "one band per edge beam"
        assert layers.count(PILLAR) >= 4, "at least the corner pillars"
