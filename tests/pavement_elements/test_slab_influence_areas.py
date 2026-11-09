from unittest.mock import Mock

import pytest

from src.pavement_elements.continuous_beam import ContinuousBeam
from src.pavement_elements.geometry_utils import calculate_polygon_area
from src.pavement_elements.slab import Slab
from src.pavement_elements.slab_edge import Edges, SupportCondition
from tests.helpers import assert_approx, centroid_preserving_beam_width

AREA_TOLERANCE = 0.01  # m² — CSV values are rounded to 2 decimal places


def make_slab(
    lx_cm: float,
    ly_cm: float,
    bottom: SupportCondition,
    left: SupportCondition,
    top: SupportCondition,
    right: SupportCondition,
) -> Slab:
    slab = Slab(("P1", "P2", "P3", "P4"), "Bedrooms")
    for edge, centerline in [
        (Edges.LEFT, 0.0),
        (Edges.RIGHT, lx_cm),
        (Edges.BOTTOM, 0.0),
        (Edges.TOP, ly_cm),
    ]:
        mock_beam = Mock(spec=ContinuousBeam)
        mock_beam.centerline = centerline
        mock_beam.width = centroid_preserving_beam_width(slab.thickness)
        slab.edges[edge].resolve_beam(mock_beam)
    slab.edges[Edges.BOTTOM].support_condition = bottom
    slab.edges[Edges.LEFT].support_condition = left
    slab.edges[Edges.TOP].support_condition = top
    slab.edges[Edges.RIGHT].support_condition = right
    return slab


def _assert_areas(
    slab: Slab,
    exp_bottom: float,
    exp_left: float,
    exp_top: float,
    exp_right: float,
) -> None:
    assert_approx(
        slab.edges[Edges.BOTTOM].influence_area,
        exp_bottom,
        "bottom influence area (m²)",
        abs_tol=AREA_TOLERANCE,
    )
    assert_approx(
        slab.edges[Edges.LEFT].influence_area,
        exp_left,
        "left influence area (m²)",
        abs_tol=AREA_TOLERANCE,
    )
    assert_approx(
        slab.edges[Edges.TOP].influence_area,
        exp_top,
        "top influence area (m²)",
        abs_tol=AREA_TOLERANCE,
    )
    assert_approx(
        slab.edges[Edges.RIGHT].influence_area,
        exp_right,
        "right influence area (m²)",
        abs_tol=AREA_TOLERANCE,
    )


# fmt: off
_SQUARE_CASES = [
    # (bottom,  left,    top,     right,  bottom, left,  top,   right)
    ("fixed",  "fixed", "fixed", "fixed",  6.25,  6.25,  6.25,  6.25),
    ("fixed",  "fixed", "pinned","fixed",  6.25,  7.57,  3.61,  7.57),
    ("fixed",  "fixed", "fixed", "pinned", 7.57,  6.25,  7.57,  3.61),
    ("pinned", "fixed", "pinned","fixed",  3.61,  8.89,  3.61,  8.89),
    ("fixed",  "pinned","fixed", "pinned", 8.89,  3.61,  8.89,  3.61),
    ("fixed",  "fixed", "pinned","pinned", 7.92,  7.92,  4.58,  4.58),
    ("fixed",  "pinned","pinned","pinned",10.05,  4.58,  5.80,  4.58),
    ("pinned", "pinned","pinned","fixed",  4.58,  5.80,  4.58, 10.05),
    ("pinned", "pinned","pinned","pinned", 6.25,  6.25,  6.25,  6.25),
]
_SQUARE_IDS = [
    "Square_all_fixed",
    "Square_top_SS_rest_fixed",
    "Square_right_SS_rest_fixed",
    "Square_left_right_fixed_top_bottom_SS",
    "Square_top_bottom_fixed_left_right_SS",
    "Square_bottom_left_fixed_top_right_SS",
    "Square_bottom_fixed_rest_SS",
    "Square_right_fixed_rest_SS",
    "Square_all_SS",
]

_RECT15_CASES = [
    ("fixed",  "fixed", "fixed", "fixed",  12.50,  6.25, 12.50,  6.25),
    ("fixed",  "fixed", "pinned","fixed",  13.73,  7.92,  7.92,  7.92),
    ("fixed",  "fixed", "fixed", "pinned", 13.82,  6.25, 13.82,  3.61),
    ("pinned", "fixed", "pinned","fixed",   8.12, 10.63,  8.12, 10.63),
    ("fixed",  "pinned","fixed", "pinned", 15.14,  3.61, 15.14,  3.61),
    ("fixed",  "fixed", "pinned","pinned", 15.85,  7.92,  9.15,  4.58),
    ("fixed",  "pinned","pinned","pinned", 17.97,  4.58, 10.38,  4.58),
    ("pinned", "pinned","pinned","fixed",  10.21,  6.25, 10.21, 10.83),
    ("pinned", "pinned","pinned","pinned", 12.50,  6.25, 12.50,  6.25),
]
_RECT15_IDS = [
    "Rect15_all_fixed",
    "Rect15_top_SS_rest_fixed",
    "Rect15_right_SS_rest_fixed",
    "Rect15_left_right_fixed_top_bottom_SS",
    "Rect15_top_bottom_fixed_left_right_SS",
    "Rect15_bottom_left_fixed_top_right_SS",
    "Rect15_bottom_fixed_rest_SS",
    "Rect15_right_fixed_rest_SS",
    "Rect15_all_SS",
]

_RECT25_CASES = [
    ("fixed",  "fixed", "fixed", "fixed",  31.25,  0.00, 31.25,  0.00),
    ("fixed",  "fixed", "pinned","fixed",  39.06,  0.00, 23.44,  0.00),
    ("fixed",  "fixed", "fixed", "pinned", 31.25,  0.00, 31.25,  0.00),
    ("pinned", "fixed", "pinned","fixed",  31.25,  0.00, 31.25,  0.00),
    ("fixed",  "pinned","fixed", "pinned", 31.25,  0.00, 31.25,  0.00),
    ("fixed",  "fixed", "pinned","pinned", 39.06,  0.00, 23.44,  0.00),
    ("fixed",  "pinned","pinned","pinned", 39.06,  0.00, 23.44,  0.00),
    ("pinned", "pinned","pinned","fixed",  31.25,  0.00, 31.25,  0.00),
    ("pinned", "pinned","pinned","pinned", 31.25,  0.00, 31.25,  0.00),
]
_RECT25_IDS = [
    "Rect25_all_fixed",
    "Rect25_top_SS_rest_fixed",
    "Rect25_right_SS_rest_fixed",
    "Rect25_left_right_fixed_top_bottom_SS",
    "Rect25_top_bottom_fixed_left_right_SS",
    "Rect25_bottom_left_fixed_top_right_SS",
    "Rect25_bottom_fixed_rest_SS",
    "Rect25_right_fixed_rest_SS",
    "Rect25_all_SS",
]

_RECTY15_CASES = [
    ("fixed",  "fixed", "fixed", "fixed",   6.25, 12.50,  6.25, 12.50),
    ("fixed",  "fixed", "pinned","fixed",   6.25, 13.82,  3.61, 13.82),
    ("fixed",  "fixed", "fixed", "pinned",  7.92, 13.73,  7.92,  7.92),
    ("pinned", "fixed", "pinned","fixed",   3.61, 15.14,  3.61, 15.14),
    ("fixed",  "pinned","fixed", "pinned", 10.63,  8.12, 10.63,  8.12),
    ("fixed",  "fixed", "pinned","pinned",  7.92, 15.85,  4.58,  9.15),
    ("fixed",  "pinned","pinned","pinned", 10.83, 10.21,  6.25, 10.21),
    ("pinned", "pinned","pinned","fixed",   4.58, 10.38,  4.58, 17.97),
    ("pinned", "pinned","pinned","pinned",  6.25, 12.50,  6.25, 12.50),
]
_RECTY15_IDS = [
    "RectY15_all_fixed",
    "RectY15_top_SS_rest_fixed",
    "RectY15_right_SS_rest_fixed",
    "RectY15_left_right_fixed_top_bottom_SS",
    "RectY15_top_bottom_fixed_left_right_SS",
    "RectY15_bottom_left_fixed_top_right_SS",
    "RectY15_bottom_fixed_rest_SS",
    "RectY15_right_fixed_rest_SS",
    "RectY15_all_SS",
]

_RECTY25_CASES = [
    ("fixed",  "fixed", "fixed", "fixed",   0.00, 31.25,  0.00, 31.25),
    ("fixed",  "fixed", "pinned","fixed",   0.00, 31.25,  0.00, 31.25),
    ("fixed",  "fixed", "fixed", "pinned",  0.00, 39.06,  0.00, 23.44),
    ("pinned", "fixed", "pinned","fixed",   0.00, 31.25,  0.00, 31.25),
    ("fixed",  "pinned","fixed", "pinned",  0.00, 31.25,  0.00, 31.25),
    ("fixed",  "fixed", "pinned","pinned",  0.00, 39.06,  0.00, 23.44),
    ("fixed",  "pinned","pinned","pinned",  0.00, 31.25,  0.00, 31.25),
    ("pinned", "pinned","pinned","fixed",   0.00, 23.44,  0.00, 39.06),
    ("pinned", "pinned","pinned","pinned",  0.00, 31.25,  0.00, 31.25),
]
_RECTY25_IDS = [
    "RectY25_all_fixed",
    "RectY25_top_SS_rest_fixed",
    "RectY25_right_SS_rest_fixed",
    "RectY25_left_right_fixed_top_bottom_SS",
    "RectY25_top_bottom_fixed_left_right_SS",
    "RectY25_bottom_left_fixed_top_right_SS",
    "RectY25_bottom_fixed_rest_SS",
    "RectY25_right_fixed_rest_SS",
    "RectY25_all_SS",
]
# fmt: on


class TestSquareSlab:
    """lx = ly = 500 cm (a/b = 1.0)"""

    @pytest.mark.parametrize(
        "bottom,left,top,right,exp_bottom,exp_left,exp_top,exp_right",
        _SQUARE_CASES,
        ids=_SQUARE_IDS,
    )
    def test_influence_areas(
        self,
        bottom: SupportCondition,
        left: SupportCondition,
        top: SupportCondition,
        right: SupportCondition,
        exp_bottom: float,
        exp_left: float,
        exp_top: float,
        exp_right: float,
    ) -> None:
        slab = make_slab(500, 500, bottom, left, top, right)
        slab.resolve_influence_areas()
        _assert_areas(slab, exp_bottom, exp_left, exp_top, exp_right)


class TestHorizontalSlabRatio15:
    """lx = 750 cm, ly = 500 cm (lx/ly = 1.5)"""

    @pytest.mark.parametrize(
        "bottom,left,top,right,exp_bottom,exp_left,exp_top,exp_right",
        _RECT15_CASES,
        ids=_RECT15_IDS,
    )
    def test_influence_areas(
        self,
        bottom: SupportCondition,
        left: SupportCondition,
        top: SupportCondition,
        right: SupportCondition,
        exp_bottom: float,
        exp_left: float,
        exp_top: float,
        exp_right: float,
    ) -> None:
        slab = make_slab(750, 500, bottom, left, top, right)
        slab.resolve_influence_areas()
        _assert_areas(slab, exp_bottom, exp_left, exp_top, exp_right)


class TestHorizontalSlabRatio25:
    """lx = 1250 cm, ly = 500 cm (lx/ly = 2.5): one-way, loads only bottom/top"""

    @pytest.mark.parametrize(
        "bottom,left,top,right,exp_bottom,exp_left,exp_top,exp_right",
        _RECT25_CASES,
        ids=_RECT25_IDS,
    )
    def test_influence_areas(
        self,
        bottom: SupportCondition,
        left: SupportCondition,
        top: SupportCondition,
        right: SupportCondition,
        exp_bottom: float,
        exp_left: float,
        exp_top: float,
        exp_right: float,
    ) -> None:
        slab = make_slab(1250, 500, bottom, left, top, right)
        slab.resolve_influence_areas()
        _assert_areas(slab, exp_bottom, exp_left, exp_top, exp_right)


class TestVerticalSlabRatio15:
    """lx = 500 cm, ly = 750 cm (ly/lx = 1.5)"""

    @pytest.mark.parametrize(
        "bottom,left,top,right,exp_bottom,exp_left,exp_top,exp_right",
        _RECTY15_CASES,
        ids=_RECTY15_IDS,
    )
    def test_influence_areas(
        self,
        bottom: SupportCondition,
        left: SupportCondition,
        top: SupportCondition,
        right: SupportCondition,
        exp_bottom: float,
        exp_left: float,
        exp_top: float,
        exp_right: float,
    ) -> None:
        slab = make_slab(500, 750, bottom, left, top, right)
        slab.resolve_influence_areas()
        _assert_areas(slab, exp_bottom, exp_left, exp_top, exp_right)


class TestVerticalSlabRatio25:
    """lx = 500 cm, ly = 1250 cm (ly/lx = 2.5): one-way, loads only left/right"""

    @pytest.mark.parametrize(
        "bottom,left,top,right,exp_bottom,exp_left,exp_top,exp_right",
        _RECTY25_CASES,
        ids=_RECTY25_IDS,
    )
    def test_influence_areas(
        self,
        bottom: SupportCondition,
        left: SupportCondition,
        top: SupportCondition,
        right: SupportCondition,
        exp_bottom: float,
        exp_left: float,
        exp_top: float,
        exp_right: float,
    ) -> None:
        slab = make_slab(500, 1250, bottom, left, top, right)
        slab.resolve_influence_areas()
        _assert_areas(slab, exp_bottom, exp_left, exp_top, exp_right)


_EDGE_ENDS = {
    Edges.BOTTOM: ((0.0, 0.0), (1.0, 0.0)),
    Edges.TOP: ((1.0, 1.0), (0.0, 1.0)),
    Edges.LEFT: ((0.0, 1.0), (0.0, 0.0)),
    Edges.RIGHT: ((1.0, 0.0), (1.0, 1.0)),
}  # edge corners as fractions of (lx, ly), in polygon order

_POLYGON_CASES = [
    # (lx, ly, bottom, left, top, right)
    (500, 500, "fixed", "fixed", "pinned", "fixed"),
    (750, 500, "fixed", "pinned", "pinned", "pinned"),
    (500, 750, "pinned", "fixed", "fixed", "pinned"),
    (1250, 500, "fixed", "pinned", "pinned", "pinned"),
    (500, 1250, "pinned", "pinned", "pinned", "fixed"),
]


class TestInfluencePolygons:
    """Each edge keeps the yield-line region whose area it carries"""

    @pytest.mark.parametrize(
        "lx_cm,ly_cm,bottom,left,top,right",
        _POLYGON_CASES,
        ids=["square", "rect_x15", "rect_y15", "one_way_x", "one_way_y"],
    )
    def test_polygons_match_areas(
        self,
        lx_cm: float,
        ly_cm: float,
        bottom: SupportCondition,
        left: SupportCondition,
        top: SupportCondition,
        right: SupportCondition,
    ) -> None:
        slab = make_slab(lx_cm, ly_cm, bottom, left, top, right)
        slab.resolve_influence_areas()
        lx, ly = (d / 100 for d in slab.effective_dimensions)
        total = 0.0
        for edge in Edges:
            slab_edge = slab.edges[edge]
            polygon = list(slab_edge.influence_polygon)
            area = calculate_polygon_area(polygon) if polygon else 0.0
            assert_approx(
                area,
                slab_edge.influence_area,
                f"{edge.value} polygon area should equal its influence area (m²)",
            )
            total += area
        assert_approx(total, lx * ly, "regions should cover the whole slab (m²)")

    @pytest.mark.parametrize(
        "lx_cm,ly_cm,bottom,left,top,right",
        _POLYGON_CASES,
        ids=["square", "rect_x15", "rect_y15", "one_way_x", "one_way_y"],
    )
    def test_polygons_start_on_their_edge(
        self,
        lx_cm: float,
        ly_cm: float,
        bottom: SupportCondition,
        left: SupportCondition,
        top: SupportCondition,
        right: SupportCondition,
    ) -> None:
        """Loaded regions start with their edge's two corners, so the edge is known"""
        slab = make_slab(lx_cm, ly_cm, bottom, left, top, right)
        slab.resolve_influence_areas()
        lx, ly = (d / 100 for d in slab.effective_dimensions)
        for edge in Edges:
            polygon = slab.edges[edge].influence_polygon
            if not polygon:
                continue
            for point, (fx, fy) in zip(polygon[:2], _EDGE_ENDS[edge], strict=True):
                assert_approx(point.x, fx * lx, f"{edge.value} corner x (m)")
                assert_approx(point.y, fy * ly, f"{edge.value} corner y (m)")

    def test_one_way_short_edges_have_no_region(self) -> None:
        slab = make_slab(1250, 500, "fixed", "pinned", "pinned", "pinned")
        slab.resolve_influence_areas()
        assert slab.edges[Edges.LEFT].influence_polygon == ()
        assert slab.edges[Edges.RIGHT].influence_polygon == ()
