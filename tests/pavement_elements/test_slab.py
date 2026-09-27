"""Tests for src/pavement_elements/slab.py."""

import math
from unittest.mock import Mock

import pytest

import src.pavement_elements.slab as _slab_module
from src.config import APP_CONFIG
from src.loading.superficial_loads import SuperficialLoads
from src.pavement_elements.continuous_beam import ContinuousBeam
from src.pavement_elements.pillar import Pillar
from src.pavement_elements.slab import (
    CORNER_EDGE_DICT,
    SLAB_MIN_THICKNESS,
    PermanentLoadDefinition,
    Slab,
)
from src.pavement_elements.slab_edge import Edges
from tests.helpers import assert_approx

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_slab_with_beams(
    lx_cm: float,
    ly_cm: float,
    local: str = "Bedrooms",
) -> Slab:
    """Build a Slab with beam-double centerlines set on all four edges.

    The slab is fully ready for dimensions / is_one_way / max_thickness reads.
    """
    s = Slab(corner_pillar_ids=("PA", "PB", "PC", "PD"), local=local)
    for edge, centerline in [
        (Edges.LEFT, 0.0),
        (Edges.RIGHT, lx_cm),
        (Edges.BOTTOM, 0.0),
        (Edges.TOP, ly_cm),
    ]:
        mock_beam = Mock(spec=ContinuousBeam)
        mock_beam.centerline = centerline
        s.edges[edge].resolve_beam(mock_beam)
    return s


# ---------------------------------------------------------------------------
# TestCornerYieldSlope
# ---------------------------------------------------------------------------


class TestCornerYieldSlope:
    """_corner_yield_slope returns the correct tangent value for each corner combo."""

    @pytest.mark.parametrize(
        "h_cond,v_cond,expected",
        [
            ("fixed", "fixed", 1.0),
            ("pinned", "pinned", 1.0),
            ("fixed", "pinned", math.sqrt(3)),
            ("pinned", "fixed", 1.0 / math.sqrt(3)),
        ],
        ids=["fixed-fixed", "pinned-pinned", "fixed-pinned", "pinned-fixed"],
    )
    def test_slope(self, h_cond: str, v_cond: str, expected: float) -> None:
        s = Slab(corner_pillar_ids=("P1", "P2", "P3", "P4"), local="Bedrooms")
        result = s._corner_yield_slope(h_cond, v_cond)  # type: ignore[arg-type]  # pyright: ignore[reportPrivateUsage]
        assert_approx(
            result, expected, f"slope({h_cond},{v_cond}) should be {expected:.4f}"
        )


# ---------------------------------------------------------------------------
# TestCornerEdgeDict
# ---------------------------------------------------------------------------


class TestCornerEdgeDict:
    """CORNER_EDGE_DICT maps each edge to its two corner keys."""

    def test_top_edge_corners(self) -> None:
        assert CORNER_EDGE_DICT[Edges.TOP] == ("top_left", "top_right"), (
            "TOP edge should map to top_left, top_right"
        )

    def test_bottom_edge_corners(self) -> None:
        assert CORNER_EDGE_DICT[Edges.BOTTOM] == ("bottom_left", "bottom_right"), (
            "BOTTOM edge should map to bottom_left, bottom_right"
        )

    def test_left_edge_corners(self) -> None:
        assert CORNER_EDGE_DICT[Edges.LEFT] == ("top_left", "bottom_left"), (
            "LEFT edge should map to top_left, bottom_left"
        )

    def test_right_edge_corners(self) -> None:
        assert CORNER_EDGE_DICT[Edges.RIGHT] == ("top_right", "bottom_right"), (
            "RIGHT edge should map to top_right, bottom_right"
        )


# ---------------------------------------------------------------------------
# TestValidatePillarCount
# ---------------------------------------------------------------------------


class TestValidatePillarCount:
    """Slab raises when constructed with fewer than 4 corner pillars."""

    def test_three_pillars_raises(self) -> None:
        with pytest.raises(ValueError, match="must have exactly 4 corner pillars"):
            Slab(corner_pillar_ids=("P1", "P2", "P3"), local="Bedrooms")  # type: ignore[arg-type]

    def test_five_pillars_raises(self) -> None:
        with pytest.raises(ValueError, match="must have exactly 4 corner pillars"):
            Slab(corner_pillar_ids=("P1", "P2", "P3", "P4", "P5"), local="Bedrooms")  # type: ignore[arg-type]


# ---------------------------------------------------------------------------
# TestAddPermanentLoad
# ---------------------------------------------------------------------------


class TestAddPermanentLoad:
    """add_permanent_load accumulates on the permanent_load field."""

    def test_accumulates(self) -> None:
        s = Slab(corner_pillar_ids=("P1", "P2", "P3", "P4"), local="Bedrooms")
        s.add_permanent_load(3.0)
        s.add_permanent_load(2.0)
        assert_approx(s.permanent_load, 5.0, "permanent_load should accumulate to 5.0")

    def test_initial_load_is_zero(self) -> None:
        s = Slab(corner_pillar_ids=("P1", "P2", "P3", "P4"), local="Bedrooms")
        assert_approx(s.permanent_load, 0.0, "initial permanent_load should be 0")


# ---------------------------------------------------------------------------
# TestDimensions
# ---------------------------------------------------------------------------


class TestDimensions:
    """dimensions returns (lx, ly) from resolved beam centerlines."""

    def test_square_slab(self) -> None:
        s = _make_slab_with_beams(500.0, 500.0)
        assert s.dimensions == (500.0, 500.0), (
            "500×500 slab should have dimensions (500, 500)"
        )

    def test_rectangular_slab(self) -> None:
        s = _make_slab_with_beams(300.0, 400.0)
        lx, ly = s.dimensions
        assert_approx(lx, 300.0, "lx should be 300 cm")
        assert_approx(ly, 400.0, "ly should be 400 cm")


# ---------------------------------------------------------------------------
# TestIsOneWay
# ---------------------------------------------------------------------------


class TestIsOneWay:
    """is_one_way is True only when max/min > 2.0 (strict)."""

    def test_square_is_two_way(self) -> None:
        s = _make_slab_with_beams(500.0, 500.0)
        assert not s.is_one_way, "square slab should be two-way"

    def test_ratio_exactly_2_is_two_way(self) -> None:
        s = _make_slab_with_beams(250.0, 500.0)
        assert not s.is_one_way, "ratio exactly 2.0 should still be two-way (strict >)"

    def test_ratio_above_2_is_one_way(self) -> None:
        s = _make_slab_with_beams(200.0, 500.0)
        assert s.is_one_way, "ratio 2.5 should be one-way"


# ---------------------------------------------------------------------------
# TestMaxThickness
# ---------------------------------------------------------------------------


class TestMaxThickness:
    """max_thickness = ceil(min(dimensions) / 3)."""

    def test_square_500(self) -> None:
        s = _make_slab_with_beams(500.0, 500.0)
        expected = math.ceil(500.0 / 3)
        assert s.max_thickness == expected, f"max_thickness should be {expected}"

    def test_rect_300x500(self) -> None:
        s = _make_slab_with_beams(300.0, 500.0)
        expected = math.ceil(300.0 / 3)
        assert s.max_thickness == expected, (
            f"max_thickness of 300×500 should be {expected}"
        )


# ---------------------------------------------------------------------------
# TestMapPillarsToCorners
# ---------------------------------------------------------------------------


class TestMapPillarsToCorners:
    """_map_pillars_to_corners assigns pillars to the correct corner keys."""

    def test_corners_assigned_correctly(self) -> None:
        p_bl = Pillar(x=0, y=0, width=20, depth=20)
        p_br = Pillar(x=300, y=0, width=20, depth=20)
        p_tl = Pillar(x=0, y=400, width=20, depth=20)
        p_tr = Pillar(x=300, y=400, width=20, depth=20)

        registry = {p_bl.id: p_bl, p_br.id: p_br, p_tl.id: p_tl, p_tr.id: p_tr}
        s = Slab(
            corner_pillar_ids=(p_bl.id, p_br.id, p_tl.id, p_tr.id), local="Bedrooms"
        )
        s._map_pillars_to_corners(registry)  # pyright: ignore[reportPrivateUsage]

        assert s.corners_pillar_dict["bottom_left"] is p_bl, (
            "bottom_left should be p_bl"
        )
        assert s.corners_pillar_dict["bottom_right"] is p_br, (
            "bottom_right should be p_br"
        )
        assert s.corners_pillar_dict["top_left"] is p_tl, "top_left should be p_tl"
        assert s.corners_pillar_dict["top_right"] is p_tr, "top_right should be p_tr"


# ---------------------------------------------------------------------------
# TestValidatePillarsExist
# ---------------------------------------------------------------------------


class TestValidatePillarsExist:
    """_validate_pillars_exist raises when a corner pillar is absent from the registry.

    NOTE: The production error message says "Beam '...' :" instead of "Slab '...' :".
    This is a copy-paste bug in the source; the test matches the actual verbatim text.
    """

    def test_missing_pillar_raises(self) -> None:
        s = Slab(
            corner_pillar_ids=("PA", "PB", "PC", "PD"),
            local="Bedrooms",
        )
        registry = {"PA": Mock(), "PB": Mock(), "PC": Mock()}  # PD is absent
        with pytest.raises(ValueError, match="does not exist in the registry"):
            s._validate_pillars_exist(registry)  # type: ignore[arg-type]  # pyright: ignore[reportPrivateUsage]


# ---------------------------------------------------------------------------
# TestNominalCovering
# ---------------------------------------------------------------------------


class TestNominalCovering:
    """Slab.nominal_covering returns the correct cover for each exposure class."""

    @pytest.mark.parametrize(
        "exposure_class,concrete,expected",
        [
            # exp1: minimum fck > 20.  C25 (25 > 20) → discount → 2.0 - 0.5 = 1.5
            (1, "C25", 1.5),
            # exp2: minimum fck > 25.  C25 (25 > 25? No) → no discount → 2.5
            (2, "C25", 2.5),
            # exp2: minimum fck > 25.  C30 (30 > 25) → discount → 2.5 - 0.5 = 2.0
            (2, "C30", 2.0),
            # exp3: minimum fck > 30.  C30 (30 > 30? No) → no discount → 3.5
            (3, "C30", 3.5),
            # exp3: minimum fck > 30.  C35 (35 > 30) → discount → 3.5 - 0.5 = 3.0
            (3, "C35", 3.0),
            # exp4: minimum fck > 40.  C40 (40 > 40? No) → no discount → 4.5
            (4, "C40", 4.5),
            # exp4: minimum fck > 40.  C45 (45 > 40) → discount → 4.5 - 0.5 = 4.0
            (4, "C45", 4.0),
        ],
        ids=[
            "exp1-C25",
            "exp2-C25-no-discount",
            "exp2-C30-discount",
            "exp3-C30-no-discount",
            "exp3-C35-discount",
            "exp4-C40-no-discount",
            "exp4-C45-discount",
        ],
    )
    def test_nominal_covering(
        self,
        exposure_class: int,
        concrete: str,
        expected: float,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        monkeypatch.setattr(APP_CONFIG, "exposure_class", exposure_class)
        monkeypatch.setattr(APP_CONFIG, "pavement_concrete", concrete)
        assert_approx(
            Slab.nominal_covering,
            expected,
            f"nominal_covering for exp{exposure_class}/{concrete}",
        )

    def test_invalid_exposure_class_raises(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setattr(APP_CONFIG, "exposure_class", 5)
        monkeypatch.setattr(APP_CONFIG, "pavement_concrete", "C30")
        with pytest.raises(ValueError, match="Invalid exposure class"):
            _ = Slab.nominal_covering


# ---------------------------------------------------------------------------
# TestPreSize (mocked SlabDeformationChecker)
# ---------------------------------------------------------------------------


class TestPreSize:
    """pre_size adjusts thickness to the minimum verified value."""

    def test_passes_immediately_returns_true(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        s = _make_slab_with_beams(300.0, 300.0)

        class _AlwaysPass:
            def __init__(self, **kw: object) -> None:
                pass

            def verify(self, h: int) -> bool:
                return True  # always pass on first try

        monkeypatch.setattr(_slab_module, "SlabDeformationChecker", _AlwaysPass)
        monkeypatch.setattr(APP_CONFIG, "pavement_concrete", "C30")

        result = s.pre_size()
        assert result, "pre_size should return True when thickness unchanged"
        assert s.thickness == SLAB_MIN_THICKNESS, (
            "thickness should stay at minimum when it passes on first try"
        )

    def test_fails_then_passes_returns_false(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        s = _make_slab_with_beams(300.0, 300.0)
        call_count: list[int] = [0]

        class _FailOnce:
            def __init__(self, **kw: object) -> None:
                pass

            def verify(self, h: int) -> bool:
                call_count[0] += 1
                return call_count[0] > 1  # fail first call, pass on second

        monkeypatch.setattr(_slab_module, "SlabDeformationChecker", _FailOnce)
        monkeypatch.setattr(APP_CONFIG, "pavement_concrete", "C30")

        result = s.pre_size()
        assert not result, "pre_size should return False when thickness changed"
        assert s.thickness == SLAB_MIN_THICKNESS + 1, (
            "thickness should increment by 1 when first check fails"
        )

    def test_exceeds_max_thickness_raises(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        s = _make_slab_with_beams(300.0, 300.0)

        class _AlwaysFail:
            def __init__(self, **kw: object) -> None:
                pass

            def verify(self, h: int) -> bool:
                return False  # never passes

        monkeypatch.setattr(_slab_module, "SlabDeformationChecker", _AlwaysFail)
        monkeypatch.setattr(APP_CONFIG, "pavement_concrete", "C30")

        with pytest.raises(ValueError, match="cannot be stabilized"):
            s.pre_size()


# ---------------------------------------------------------------------------
# TestResolveLoads (mocked SuperficialLoads)
# ---------------------------------------------------------------------------


class TestResolveLoads:
    """_resolve_permanent_load_without_own_weight / _resolve_variable_load use SuperficialLoads."""

    def test_permanent_load_sums_finish_ceiling_infill(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setattr(
            SuperficialLoads,
            "get_top_finish_weight",
            lambda *a: 1.5,  # type: ignore
        )
        monkeypatch.setattr(SuperficialLoads, "get_ceiling_weight", lambda *a: 0.5)  # type: ignore
        monkeypatch.setattr(SuperficialLoads, "get_infill_weight", lambda *a: 0.8)  # type: ignore

        s = Slab(
            corner_pillar_ids=("P1", "P2", "P3", "P4"),
            local="Bedrooms",
            top_finish=PermanentLoadDefinition("mat", 2.0),
            ceiling_finish="plaster",
            infill=PermanentLoadDefinition("sand", 3.0),
        )
        s._resolve_permanent_load_without_own_weight()  # pyright: ignore[reportPrivateUsage]

        assert_approx(
            s.permanent_load, 2.8, "permanent_load should sum finish + ceiling + infill"
        )

    def test_variable_load_set_from_superficial_loads(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setattr(
            SuperficialLoads,
            "get_variable_usage_load",
            lambda local: 1.5,  # pyright: ignore
        )

        s = Slab(corner_pillar_ids=("P1", "P2", "P3", "P4"), local="Bedrooms")
        s._resolve_variable_load()  # pyright: ignore[reportPrivateUsage]

        assert_approx(
            s.variable_load, 1.5, "variable_load should come from SuperficialLoads"
        )
