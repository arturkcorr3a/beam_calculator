"""Tests for src/pavement_elements/slab.py."""

import math
from unittest.mock import Mock

import pytest

import src.pavement_elements.slab as _slab_module
from src.config import APP_CONFIG
from src.config_options import ExposureClass
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
from src.properties.concrete import Concrete
from tests.helpers import assert_approx, centroid_preserving_beam_width

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_slab_with_beams(
    lx_cm: float,
    ly_cm: float,
    local: str = "Bedrooms",
    beam_width: float | None = None,
) -> Slab:
    """Build a Slab with beam-double centerlines set on all four edges.

    The slab is fully ready for dimensions / is_one_way / max_thickness reads.

    Args:
        beam_width: Width of every supporting beam double (cm). Defaults to the
            centroid-preserving width for the slab's thickness, so the
            effective spans equal the centerline distances.
    """
    s = Slab(corner_pillar_ids=("PA", "PB", "PC", "PD"), local=local)
    if beam_width is None:
        beam_width = centroid_preserving_beam_width(s.thickness)
    for edge, centerline in [
        (Edges.LEFT, 0.0),
        (Edges.RIGHT, lx_cm),
        (Edges.BOTTOM, 0.0),
        (Edges.TOP, ly_cm),
    ]:
        mock_beam = Mock(spec=ContinuousBeam)
        mock_beam.centerline = centerline
        mock_beam.width = beam_width
        s.edges[edge].resolve_beam(mock_beam)
    return s


_CHECK_RESULT_SENTINEL = object()  # stands in for a DeformationCheckResult
_SUPPORT_CASE_DOUBLE = 4  # Carvalho Quadro 7.2 case reported by the checker doubles


class _CheckerDouble:
    """Base for SlabDeformationChecker doubles: the members pre_size reads after its loop."""

    supporting_case = _SUPPORT_CASE_DOUBLE

    def result(self) -> object:
        return _CHECK_RESULT_SENTINEL


def _skip_support_resolution(monkeypatch: pytest.MonkeyPatch, slab: Slab) -> None:
    """Make resolve_support_conditions a no-op (the beam doubles carry no spans)."""
    monkeypatch.setattr(slab, "resolve_support_conditions", lambda registry: None)  # pyright: ignore


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
# TestEffectiveDimensions
# ---------------------------------------------------------------------------


class TestEffectiveDimensions:
    """effective_dimensions applies the NBR 6118 §14.7.2.2 0.3h cap to beam supports."""

    def test_narrow_beams_keep_centerline_distance(self) -> None:
        s = _make_slab_with_beams(500.0, 400.0, beam_width=4.0)
        s.thickness = 10
        # t/2 = 2 < 0.3h = 3 -> l_ef == centerline distance
        lx, ly = s.effective_dimensions
        assert_approx(lx, 500.0, "lx should equal the centerline distance")
        assert_approx(ly, 400.0, "ly should equal the centerline distance")

    def test_wide_beams_capped_at_0_3h(self) -> None:
        s = _make_slab_with_beams(500.0, 400.0, beam_width=20.0)
        s.thickness = 10
        # l0 = 480 / 380; a = min(10, 3) = 3 on each side
        lx, ly = s.effective_dimensions
        assert_approx(lx, 486.0, "lx should be l0 + 2 * 0.3h")
        assert_approx(ly, 386.0, "ly should be l0 + 2 * 0.3h")

    def test_follows_thickness_changes(self) -> None:
        s = _make_slab_with_beams(500.0, 400.0, beam_width=20.0)
        s.thickness = 10
        _ = s.effective_dimensions
        s.thickness = 20
        # a = min(10, 6) = 6 -> 480 + 12
        lx, _ly = s.effective_dimensions
        assert_approx(lx, 492.0, "effective_dimensions should not be cached")


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
    """_validate_pillars_exist raises when a corner pillar is absent from the registry."""

    def test_missing_pillar_raises(self) -> None:
        s = Slab(
            corner_pillar_ids=("PA", "PB", "PC", "PD"),
            local="Bedrooms",
        )
        registry = {"PA": Mock(), "PB": Mock(), "PC": Mock()}  # PD is absent
        with pytest.raises(ValueError, match="does not exist in the registry"):
            s._validate_pillars_exist(registry)  # type: ignore[arg-type]  # pyright: ignore[reportPrivateUsage]

    def test_message_names_the_slab(self) -> None:
        s = Slab(
            corner_pillar_ids=("PA", "PB", "PC", "PD"),
            local="Bedrooms",
        )
        registry = {"PA": Mock(), "PB": Mock(), "PC": Mock()}  # PD is absent
        with pytest.raises(ValueError, match=rf"^Slab '{s.id}': pillar 'PD'"):
            s._validate_pillars_exist(registry)  # type: ignore[arg-type]  # pyright: ignore[reportPrivateUsage]


class TestResolveEdgeMessage:
    """_resolve_edge names the edge by its plain value when no beam supports it."""

    def test_missing_beam_message_uses_edge_value(self) -> None:
        s = Slab(corner_pillar_ids=("PA", "PB", "PC", "PD"), local="Bedrooms")
        s.corners_pillar_dict = {
            "bottom_left": Pillar(0.0, 0.0, 20.0, 30.0),
            "bottom_right": Pillar(500.0, 0.0, 20.0, 30.0),
            "top_left": Pillar(0.0, 400.0, 20.0, 30.0),
            "top_right": Pillar(500.0, 400.0, 20.0, 30.0),
        }
        with pytest.raises(ValueError, match=r"No valid beam found for top edge\.$"):
            s._resolve_edge(Edges.TOP, {})  # pyright: ignore[reportPrivateUsage]


# ---------------------------------------------------------------------------
# TestNominalCovering
# ---------------------------------------------------------------------------


class TestNominalCovering:
    """Slab.nominal_covering returns the correct cover for each exposure class."""

    @pytest.mark.parametrize(
        "exposure_class,concrete,expected",
        [
            # exp1: minimum fck > 20.  C25 (25 > 20) → discount → 2.0 - 0.5 = 1.5
            (ExposureClass.WEAK, Concrete.C25, 1.5),
            # exp2: minimum fck > 25.  C25 (25 > 25? No) → no discount → 2.5
            (ExposureClass.MODERATE, Concrete.C25, 2.5),
            # exp2: minimum fck > 25.  C30 (30 > 25) → discount → 2.5 - 0.5 = 2.0
            (ExposureClass.MODERATE, Concrete.C30, 2.0),
            # exp3: minimum fck > 30.  C30 (30 > 30? No) → no discount → 3.5
            (ExposureClass.SEVERE, Concrete.C30, 3.5),
            # exp3: minimum fck > 30.  C35 (35 > 30) → discount → 3.5 - 0.5 = 3.0
            (ExposureClass.SEVERE, Concrete.C35, 3.0),
            # exp4: minimum fck > 40.  C40 (40 > 40? No) → no discount → 4.5
            (ExposureClass.VERY_SEVERE, Concrete.C40, 4.5),
            # exp4: minimum fck > 40.  C45 (45 > 40) → discount → 4.5 - 0.5 = 4.0
            (ExposureClass.VERY_SEVERE, Concrete.C45, 4.0),
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
        exposure_class: ExposureClass,
        concrete: Concrete,
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


# ---------------------------------------------------------------------------
# TestPreSize (mocked SlabDeformationChecker)
# ---------------------------------------------------------------------------


class TestPreSize:
    """pre_size adjusts thickness to the minimum verified value."""

    def test_passes_immediately_returns_true(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        s = _make_slab_with_beams(300.0, 300.0)

        class _AlwaysPass(_CheckerDouble):
            def __init__(self, **kw: object) -> None:
                pass

            def verify(self, h: int) -> bool:
                return True  # always pass on first try

        monkeypatch.setattr(_slab_module, "SlabDeformationChecker", _AlwaysPass)
        monkeypatch.setattr(APP_CONFIG, "pavement_concrete", Concrete.C30)
        _skip_support_resolution(monkeypatch, s)

        result = s.pre_size({})
        assert result, "pre_size should return True when thickness unchanged"
        assert s.thickness == SLAB_MIN_THICKNESS, (
            "thickness should stay at minimum when it passes on first try"
        )

    def test_fails_then_passes_returns_false(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        s = _make_slab_with_beams(300.0, 300.0)
        call_count: list[int] = [0]

        class _FailOnce(_CheckerDouble):
            def __init__(self, **kw: object) -> None:
                pass

            def verify(self, h: int) -> bool:
                call_count[0] += 1
                return call_count[0] > 1  # fail first call, pass on second

        monkeypatch.setattr(_slab_module, "SlabDeformationChecker", _FailOnce)
        monkeypatch.setattr(APP_CONFIG, "pavement_concrete", Concrete.C30)
        _skip_support_resolution(monkeypatch, s)

        result = s.pre_size({})
        assert not result, "pre_size should return False when thickness changed"
        assert s.thickness == SLAB_MIN_THICKNESS + 1, (
            "thickness should increment by 1 when first check fails"
        )

    def test_exceeds_max_thickness_raises(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        s = _make_slab_with_beams(300.0, 300.0)

        class _AlwaysFail(_CheckerDouble):
            def __init__(self, **kw: object) -> None:
                pass

            def verify(self, h: int) -> bool:
                return False  # never passes

        monkeypatch.setattr(_slab_module, "SlabDeformationChecker", _AlwaysFail)
        monkeypatch.setattr(APP_CONFIG, "pavement_concrete", Concrete.C30)
        _skip_support_resolution(monkeypatch, s)

        with pytest.raises(ValueError, match="cannot be stabilized"):
            s.pre_size({})

    def test_checker_spans_follow_thickness(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        s = _make_slab_with_beams(300.0, 400.0, beam_width=20.0)
        verified_spans: list[tuple[float, float, float]] = []

        class _PassAtThird(_CheckerDouble):
            def __init__(self, *, lx: float, ly: float, **kw: object) -> None:
                self.lx = lx
                self.ly = ly
                self.span = min(lx, ly)

            def verify(self, h: int) -> bool:
                verified_spans.append((self.lx, self.ly, self.span))
                return len(verified_spans) == 3

        monkeypatch.setattr(_slab_module, "SlabDeformationChecker", _PassAtThird)
        monkeypatch.setattr(APP_CONFIG, "pavement_concrete", Concrete.C30)
        _skip_support_resolution(monkeypatch, s)

        s.pre_size({})
        # h = 8, 9, 10 -> a = 0.3h = 2.4, 2.7, 3.0; l0 = 280 / 380
        for (lx, ly, span), a in zip(verified_spans, (2.4, 2.7, 3.0)):
            assert_approx(lx, 280 + 2 * a, f"checker lx should match h = {a / 0.3:.0f}")
            assert_approx(ly, 380 + 2 * a, f"checker ly should match h = {a / 0.3:.0f}")
            assert_approx(span, 280 + 2 * a, "checker span should be min(lx, ly)")

    def test_support_conditions_re_resolved_at_each_thickness(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """The checker sees the support conditions resolved for the current thickness."""
        s = _make_slab_with_beams(300.0, 300.0)
        seen: list[tuple[int, str]] = []

        def _fix_bottom_from_9_cm(registry: dict[str, Pillar]) -> None:
            s.edges[Edges.BOTTOM].support_condition = (
                "fixed" if s.thickness >= 9 else "pinned"
            )

        class _RecordConditions(_CheckerDouble):
            def __init__(
                self, *, support_conditions: dict[Edges, str], **kw: object
            ) -> None:
                self.support_conditions = support_conditions

            def verify(self, h: int) -> bool:
                seen.append((h, self.support_conditions[Edges.BOTTOM]))
                return h >= 10

        monkeypatch.setattr(_slab_module, "SlabDeformationChecker", _RecordConditions)
        monkeypatch.setattr(APP_CONFIG, "pavement_concrete", Concrete.C30)
        monkeypatch.setattr(s, "resolve_support_conditions", _fix_bottom_from_9_cm)

        s.pre_size({})

        assert seen == [(8, "pinned"), (9, "fixed"), (10, "fixed")], (
            "checker conditions should follow the thickness being tried"
        )

    def test_stores_the_passing_check(self, monkeypatch: pytest.MonkeyPatch) -> None:
        s = _make_slab_with_beams(300.0, 300.0)

        class _PassAtNine(_CheckerDouble):
            def __init__(self, **kw: object) -> None:
                pass

            def verify(self, h: int) -> bool:
                return h >= 9

        monkeypatch.setattr(_slab_module, "SlabDeformationChecker", _PassAtNine)
        monkeypatch.setattr(APP_CONFIG, "pavement_concrete", Concrete.C30)
        _skip_support_resolution(monkeypatch, s)

        s.pre_size({})
        assert s.deflection_check is _CHECK_RESULT_SENTINEL, (
            "pre_size should keep the checker's result after the loop"
        )
        assert s.deflection_support_case == _SUPPORT_CASE_DOUBLE, (
            "pre_size should keep the checker's support case"
        )

    def test_failure_keeps_no_check(self, monkeypatch: pytest.MonkeyPatch) -> None:
        s = _make_slab_with_beams(300.0, 300.0)

        class _AlwaysFail(_CheckerDouble):
            def __init__(self, **kw: object) -> None:
                pass

            def verify(self, h: int) -> bool:
                return False

        monkeypatch.setattr(_slab_module, "SlabDeformationChecker", _AlwaysFail)
        monkeypatch.setattr(APP_CONFIG, "pavement_concrete", Concrete.C30)
        _skip_support_resolution(monkeypatch, s)

        with pytest.raises(ValueError, match="cannot be stabilized"):
            s.pre_size({})
        assert s.deflection_check is None, "a failed pre_size should store no check"


class TestClearResolvedDeflection:
    """clear_resolved forgets the stored deflection check."""

    def test_resets_check_and_support_case(self) -> None:
        s = Slab(corner_pillar_ids=("PA", "PB", "PC", "PD"), local="Bedrooms")
        s.deflection_check = _CHECK_RESULT_SENTINEL  # type: ignore[assignment]  # pyright: ignore[reportAttributeAccessIssue]
        s.deflection_support_case = _SUPPORT_CASE_DOUBLE
        s.clear_resolved()
        assert s.deflection_check is None, "deflection_check should be cleared"
        assert s.deflection_support_case is None, (
            "deflection_support_case should be cleared"
        )


# ---------------------------------------------------------------------------
# TestLowered
# ---------------------------------------------------------------------------


def _set_beam_heights(slab: Slab, heights: dict[Edges, float]) -> None:
    """Give each edge's beam double an id and a height (cm)."""
    for edge, height in heights.items():
        beam = slab.edges[edge].beam
        beam.id = f"V_{edge.value}"
        beam.height = height


class TestLowered:
    """lowered (cm) validation and the max_lowered limit."""

    def test_defaults_to_zero(self) -> None:
        s = Slab(corner_pillar_ids=("P1", "P2", "P3", "P4"), local="Bedrooms")
        assert s.lowered == 0, "lowered should default to 0 cm"
        assert not s.is_lowered, "a slab with lowered = 0 is not lowered"

    def test_positive_is_lowered(self) -> None:
        s = Slab(
            corner_pillar_ids=("P1", "P2", "P3", "P4"), local="Bedrooms", lowered=5
        )
        assert s.is_lowered, "a slab with lowered > 0 is lowered"

    def test_negative_raises(self) -> None:
        with pytest.raises(ValueError, match="lowered must be >= 0"):
            Slab(
                corner_pillar_ids=("P1", "P2", "P3", "P4"), local="Bedrooms", lowered=-1
            )

    def test_max_lowered_uses_shortest_beam(self) -> None:
        s = _make_slab_with_beams(300.0, 300.0)
        _set_beam_heights(
            s,
            {Edges.LEFT: 40.0, Edges.RIGHT: 50.0, Edges.BOTTOM: 30.0, Edges.TOP: 45.0},
        )
        s.thickness = 10
        assert_approx(s.max_lowered, 20.0, "max_lowered should be 30 - 10 cm")

    def test_validate_at_limit_passes(self) -> None:
        s = _make_slab_with_beams(300.0, 300.0)
        _set_beam_heights(s, {edge: 30.0 for edge in Edges})
        s.thickness = 10
        s.lowered = 20
        s.validate_lowered()  # should not raise

    def test_validate_above_limit_raises(self) -> None:
        s = _make_slab_with_beams(300.0, 300.0)
        _set_beam_heights(
            s,
            {Edges.LEFT: 40.0, Edges.RIGHT: 40.0, Edges.BOTTOM: 30.0, Edges.TOP: 40.0},
        )
        s.thickness = 10
        s.lowered = 21
        with pytest.raises(ValueError, match="V_bottom"):
            s.validate_lowered()


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


# ---------------------------------------------------------------------------
# TestUnloadOnSupportingSpans
# ---------------------------------------------------------------------------


class TestUnloadOnSupportingSpans:
    """unload_on_supporting_spans skips edges that carry no load."""

    def _record_unloads(self, s: Slab, monkeypatch: pytest.MonkeyPatch) -> list[Edges]:
        """Replace each edge's unload_on_spans with a recorder of the edge name"""
        unloaded: list[Edges] = []
        for edge in Edges:
            monkeypatch.setattr(
                s.edges[edge],
                "unload_on_spans",
                lambda registry, e=edge: unloaded.append(e),  # pyright: ignore
            )
        return unloaded

    def test_one_way_horizontal_unloads_only_bottom_and_top(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        s = _make_slab_with_beams(1250.0, 500.0)
        unloaded = self._record_unloads(s, monkeypatch)
        s.unload_on_supporting_spans({})
        assert unloaded == [Edges.BOTTOM, Edges.TOP], (
            "one-way slab along x should unload only on bottom/top beams"
        )

    def test_one_way_vertical_unloads_only_left_and_right(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        s = _make_slab_with_beams(500.0, 1250.0)
        unloaded = self._record_unloads(s, monkeypatch)
        s.unload_on_supporting_spans({})
        assert unloaded == [Edges.LEFT, Edges.RIGHT], (
            "one-way slab along y should unload only on left/right beams"
        )

    def test_two_way_unloads_all_edges(self, monkeypatch: pytest.MonkeyPatch) -> None:
        s = _make_slab_with_beams(500.0, 500.0)
        unloaded = self._record_unloads(s, monkeypatch)
        s.unload_on_supporting_spans({})
        assert unloaded == list(Edges), "two-way slab should unload on all four edges"
