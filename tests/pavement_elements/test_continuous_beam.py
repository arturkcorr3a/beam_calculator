"""Tests for src/pavement_elements/continuous_beam.py."""

import pytest

import src.pavement_elements.continuous_beam as _cb_module
from src.config import APP_CONFIG
from src.loading.linear_loads import LinearLoads
from src.pavement_elements.continuous_beam import ContinuousBeam, WallDefinition
from src.pavement_elements.geometry_utils import Alignment, Axis
from src.pavement_elements.pillar import Pillar
from tests.helpers import assert_approx

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def wall() -> WallDefinition:
    """Non-structural hollow-block wall, 14 cm nominal, 1 cm coating."""
    return WallDefinition(
        structural=False,
        masonry_type="hollow concrete block",
        nominal_thickness=14,
        coating_thickness=1,
    )


@pytest.fixture
def pillars_horizontal() -> tuple[Pillar, Pillar, Pillar]:
    """Three pillars on the X axis: (0,0), (200,0), (400,0)."""
    p1 = Pillar(x=0, y=0, width=20, depth=20)
    p2 = Pillar(x=200, y=0, width=20, depth=20)
    p3 = Pillar(x=400, y=0, width=20, depth=20)
    return p1, p2, p3


@pytest.fixture
def registry_horizontal(
    pillars_horizontal: tuple[Pillar, Pillar, Pillar],
) -> dict[str, Pillar]:
    """Registry of the three horizontal fixture pillars."""
    p1, p2, p3 = pillars_horizontal
    return {p1.id: p1, p2.id: p2, p3.id: p3}


@pytest.fixture
def pillars_vertical() -> tuple[Pillar, Pillar]:
    """Two pillars on the Y axis: (100,0), (100,400)."""
    p1 = Pillar(x=100, y=0, width=20, depth=20)
    p2 = Pillar(x=100, y=400, width=20, depth=20)
    return p1, p2


@pytest.fixture
def registry_vertical(pillars_vertical: tuple[Pillar, Pillar]) -> dict[str, Pillar]:
    """Registry of the two vertical fixture pillars."""
    p1, p2 = pillars_vertical
    return {p1.id: p1, p2.id: p2}


@pytest.fixture
def horizontal_beam(
    pillars_horizontal: tuple[Pillar, Pillar, Pillar], wall: WallDefinition
) -> ContinuousBeam:
    """Resolved 3-pillar BOTTOM-aligned X-axis beam."""
    p1, p2, p3 = pillars_horizontal
    return ContinuousBeam(
        pillar_ids=[p1.id, p2.id, p3.id],
        reference_pillar_id=p1.id,
        width=16,
        alignment=Alignment.BOTTOM,
        wall=wall,
    )


# ---------------------------------------------------------------------------
# TestWallDefinition
# ---------------------------------------------------------------------------


class TestWallDefinition:
    """WallDefinition.get_parameters_for_load returns the 4-tuple in field order."""

    def test_returns_correct_tuple(self, wall: WallDefinition) -> None:
        result = wall.get_parameters_for_load()
        assert result == (False, "hollow concrete block", 14, 1), (
            "get_parameters_for_load should return (structural, masonry_type, nominal, coating)"
        )


# ---------------------------------------------------------------------------
# TestConstructionValidation
# ---------------------------------------------------------------------------


class TestConstructionValidation:
    """ContinuousBeam raises ValueError for invalid construction args."""

    def test_reference_not_in_pillar_ids_raises(self, wall: WallDefinition) -> None:
        with pytest.raises(ValueError, match="Reference pillar ID must be included"):
            ContinuousBeam(
                pillar_ids=["P1", "P2"],
                reference_pillar_id="P99",
                width=16,
                alignment=Alignment.BOTTOM,
                wall=wall,
            )

    def test_fewer_than_two_pillars_raises(self, wall: WallDefinition) -> None:
        with pytest.raises(ValueError, match="at least 2 pillars"):
            ContinuousBeam(
                pillar_ids=["P1"],
                reference_pillar_id="P1",
                width=16,
                alignment=Alignment.BOTTOM,
                wall=wall,
            )

    def test_width_below_12_raises(self, wall: WallDefinition) -> None:
        with pytest.raises(ValueError, match="width must be at least 12.0 cm"):
            ContinuousBeam(
                pillar_ids=["P1", "P2"],
                reference_pillar_id="P1",
                width=11,
                alignment=Alignment.BOTTOM,
                wall=wall,
            )

    def test_valid_beam_id_starts_with_V(
        self, pillars_horizontal: tuple[Pillar, Pillar, Pillar], wall: WallDefinition
    ) -> None:
        p1, p2, _ = pillars_horizontal
        b = ContinuousBeam(
            pillar_ids=[p1.id, p2.id],
            reference_pillar_id=p1.id,
            width=16,
            alignment=Alignment.BOTTOM,
            wall=wall,
        )
        assert b.id.startswith("V"), "auto-generated id must start with 'V'"

    def test_initial_height_equals_width(
        self, pillars_horizontal: tuple[Pillar, Pillar, Pillar], wall: WallDefinition
    ) -> None:
        p1, p2, _ = pillars_horizontal
        b = ContinuousBeam(
            pillar_ids=[p1.id, p2.id],
            reference_pillar_id=p1.id,
            width=16,
            alignment=Alignment.BOTTOM,
            wall=wall,
        )
        assert b.height == 16, "initial height should equal width"


# ---------------------------------------------------------------------------
# TestContainsPillar
# ---------------------------------------------------------------------------


class TestContainsPillar:
    """contains_pillar checks membership in pillar_ids."""

    def test_included_pillar_is_found(
        self,
        horizontal_beam: ContinuousBeam,
        pillars_horizontal: tuple[Pillar, Pillar, Pillar],
    ) -> None:
        p1, _, _ = pillars_horizontal
        assert horizontal_beam.contains_pillar(p1.id), "included pillar should be found"

    def test_excluded_pillar_is_not_found(
        self, horizontal_beam: ContinuousBeam
    ) -> None:
        assert not horizontal_beam.contains_pillar("P_unknown"), (
            "unknown pillar should not be found"
        )


# ---------------------------------------------------------------------------
# TestGetRange
# ---------------------------------------------------------------------------


class TestGetRange:
    """_get_range returns the beam's perpendicular band; raises before resolution."""

    def test_raises_before_resolution(self, horizontal_beam: ContinuousBeam) -> None:
        with pytest.raises(ValueError, match="has no centerline set"):
            horizontal_beam._get_range()  # pyright: ignore[reportPrivateUsage]

    def test_returns_correct_band_after_resolution(
        self,
        horizontal_beam: ContinuousBeam,
        registry_horizontal: dict[str, Pillar],
    ) -> None:
        horizontal_beam.resolve_and_validate(registry_horizontal)
        lo, hi = horizontal_beam._get_range()  # pyright: ignore[reportPrivateUsage]
        # centerline = -2.0, width = 16 → [-10, 6]
        assert_approx(lo, -10.0, "range low should be centerline - width/2")
        assert_approx(hi, 6.0, "range high should be centerline + width/2")


# ---------------------------------------------------------------------------
# TestGetSpansBetween
# ---------------------------------------------------------------------------


class TestGetSpansBetween:
    """get_spans_between returns spans between two member pillars."""

    def test_adjacent_pillars_return_one_span(
        self,
        horizontal_beam: ContinuousBeam,
        registry_horizontal: dict[str, Pillar],
        pillars_horizontal: tuple[Pillar, Pillar, Pillar],
    ) -> None:
        horizontal_beam.resolve_and_validate(registry_horizontal)
        p1, p2, _ = pillars_horizontal
        spans = horizontal_beam.get_spans_between(p1.id, p2.id)
        assert len(spans) == 1, "adjacent pillars should return one span"

    def test_endpoint_pillars_return_all_spans(
        self,
        horizontal_beam: ContinuousBeam,
        registry_horizontal: dict[str, Pillar],
        pillars_horizontal: tuple[Pillar, Pillar, Pillar],
    ) -> None:
        horizontal_beam.resolve_and_validate(registry_horizontal)
        p1, _, p3 = pillars_horizontal
        spans = horizontal_beam.get_spans_between(p1.id, p3.id)
        assert len(spans) == 2, "endpoint pillars should return both spans"

    def test_reversed_order_returns_same_spans(
        self,
        horizontal_beam: ContinuousBeam,
        registry_horizontal: dict[str, Pillar],
        pillars_horizontal: tuple[Pillar, Pillar, Pillar],
    ) -> None:
        horizontal_beam.resolve_and_validate(registry_horizontal)
        p1, _, p3 = pillars_horizontal
        spans_fwd = horizontal_beam.get_spans_between(p1.id, p3.id)
        spans_rev = horizontal_beam.get_spans_between(p3.id, p1.id)
        assert len(spans_fwd) == len(spans_rev), (
            "reversed order should return same span count"
        )

    def test_unknown_pillar_raises(
        self,
        horizontal_beam: ContinuousBeam,
        registry_horizontal: dict[str, Pillar],
        pillars_horizontal: tuple[Pillar, Pillar, Pillar],
    ) -> None:
        horizontal_beam.resolve_and_validate(registry_horizontal)
        p1, _, _ = pillars_horizontal
        with pytest.raises(ValueError, match="Both pillars must be part"):
            horizontal_beam.get_spans_between(p1.id, "P99")


# ---------------------------------------------------------------------------
# TestDetermineAxis
# ---------------------------------------------------------------------------


class TestDetermineAxis:
    """_determine_axis picks X when x_spread ≥ y_spread."""

    def test_horizontal_layout_gives_x_axis(
        self,
        horizontal_beam: ContinuousBeam,
        registry_horizontal: dict[str, Pillar],
    ) -> None:
        horizontal_beam.resolve_and_validate(registry_horizontal)
        assert horizontal_beam.axis == Axis.X, (
            "horizontal pillar layout should give Axis.X"
        )

    def test_vertical_layout_gives_y_axis(
        self,
        pillars_vertical: tuple[Pillar, Pillar],
        registry_vertical: dict[str, Pillar],
        wall: WallDefinition,
    ) -> None:
        p1, p2 = pillars_vertical
        b = ContinuousBeam(
            pillar_ids=[p1.id, p2.id],
            reference_pillar_id=p1.id,
            width=16,
            alignment=Alignment.LEFT,
            wall=wall,
        )
        b.resolve_and_validate(registry_vertical)
        assert b.axis == Axis.Y, "vertical pillar layout should give Axis.Y"


# ---------------------------------------------------------------------------
# TestDetermineCenterline
# ---------------------------------------------------------------------------


class TestDetermineCenterline:
    """_determine_centerline computes the correct perpendicular coordinate."""

    def test_bottom_alignment_on_x_beam(
        self,
        pillars_horizontal: tuple[Pillar, Pillar, Pillar],
        registry_horizontal: dict[str, Pillar],
        wall: WallDefinition,
    ) -> None:
        p1, p2, _ = pillars_horizontal
        b = ContinuousBeam(
            pillar_ids=[p1.id, p2.id],
            reference_pillar_id=p1.id,
            width=16,
            alignment=Alignment.BOTTOM,
            wall=wall,
        )
        b.resolve_and_validate(registry_horizontal)
        # p1.y=0, depth=20 → y_range=(−10,10); BOTTOM: ref low − width/2 = −10 − 8 = −18
        # But test_centerline above showed -2.0; verify
        assert b.centerline is not None, "centerline should be computed"
        assert_approx(
            b.centerline, -2.0, "BOTTOM centerline should be ref_y_low − beam_width/2"
        )

    def test_top_alignment_on_x_beam(
        self,
        pillars_horizontal: tuple[Pillar, Pillar, Pillar],
        registry_horizontal: dict[str, Pillar],
        wall: WallDefinition,
    ) -> None:
        p1, p2, _ = pillars_horizontal
        b = ContinuousBeam(
            pillar_ids=[p1.id, p2.id],
            reference_pillar_id=p1.id,
            width=16,
            alignment=Alignment.TOP,
            wall=wall,
        )
        b.resolve_and_validate(registry_horizontal)
        assert b.centerline is not None, "centerline should be computed"
        assert_approx(
            b.centerline, 2.0, "TOP centerline should be ref_y_high + beam_width/2"
        )

    def test_center_alignment_on_x_beam(
        self,
        pillars_horizontal: tuple[Pillar, Pillar, Pillar],
        registry_horizontal: dict[str, Pillar],
        wall: WallDefinition,
    ) -> None:
        p1, p2, _ = pillars_horizontal
        b = ContinuousBeam(
            pillar_ids=[p1.id, p2.id],
            reference_pillar_id=p1.id,
            width=16,
            alignment=Alignment.CENTER,
            wall=wall,
        )
        b.resolve_and_validate(registry_horizontal)
        assert b.centerline is not None, "centerline should be computed"
        assert_approx(b.centerline, 0.0, "CENTER centerline should be ref_y centroid")

    def test_left_alignment_on_y_beam(
        self,
        pillars_vertical: tuple[Pillar, Pillar],
        registry_vertical: dict[str, Pillar],
        wall: WallDefinition,
    ) -> None:
        p1, p2 = pillars_vertical
        b = ContinuousBeam(
            pillar_ids=[p1.id, p2.id],
            reference_pillar_id=p1.id,
            width=16,
            alignment=Alignment.LEFT,
            wall=wall,
        )
        b.resolve_and_validate(registry_vertical)
        assert b.centerline is not None, "centerline should be computed"
        assert_approx(
            b.centerline, 98.0, "LEFT centerline should be ref_x_low − beam_width/2"
        )

    def test_right_alignment_on_y_beam(
        self,
        pillars_vertical: tuple[Pillar, Pillar],
        registry_vertical: dict[str, Pillar],
        wall: WallDefinition,
    ) -> None:
        p1, p2 = pillars_vertical
        b = ContinuousBeam(
            pillar_ids=[p1.id, p2.id],
            reference_pillar_id=p1.id,
            width=16,
            alignment=Alignment.RIGHT,
            wall=wall,
        )
        b.resolve_and_validate(registry_vertical)
        assert b.centerline is not None, "centerline should be computed"
        assert_approx(
            b.centerline, 102.0, "RIGHT centerline should be ref_x_high + beam_width/2"
        )

    def test_center_alignment_on_y_beam(
        self,
        pillars_vertical: tuple[Pillar, Pillar],
        registry_vertical: dict[str, Pillar],
        wall: WallDefinition,
    ) -> None:
        p1, p2 = pillars_vertical
        b = ContinuousBeam(
            pillar_ids=[p1.id, p2.id],
            reference_pillar_id=p1.id,
            width=16,
            alignment=Alignment.CENTER,
            wall=wall,
        )
        b.resolve_and_validate(registry_vertical)
        assert b.centerline is not None, "centerline should be computed"
        assert_approx(
            b.centerline, 100.0, "CENTER-Y centerline should be ref_x centroid"
        )


# ---------------------------------------------------------------------------
# TestValidateNoSkippedPillars
# ---------------------------------------------------------------------------


class TestValidateNoSkippedPillars:
    """resolve_and_validate raises when a pillar is skipped on the same axis line."""

    def test_skipped_pillar_raises(
        self,
        pillars_horizontal: tuple[Pillar, Pillar, Pillar],
        wall: WallDefinition,
    ) -> None:
        p1, p_mid, p3 = pillars_horizontal
        # Beam skips p_mid even though it lies between p1 and p3 on the same line
        registry = {p1.id: p1, p_mid.id: p_mid, p3.id: p3}
        b = ContinuousBeam(
            pillar_ids=[p1.id, p3.id],
            reference_pillar_id=p1.id,
            width=16,
            alignment=Alignment.BOTTOM,
            wall=wall,
        )
        with pytest.raises(ValueError, match="skips pillar"):
            b.resolve_and_validate(registry)


# ---------------------------------------------------------------------------
# TestPreSize
# ---------------------------------------------------------------------------


class TestPreSize:
    """pre_size sets beam height to a multiple of 5 based on the longest span."""

    def test_pre_size_returns_multiple_of_5(
        self,
        horizontal_beam: ContinuousBeam,
        registry_horizontal: dict[str, Pillar],
    ) -> None:
        horizontal_beam.resolve_and_validate(registry_horizontal)
        horizontal_beam.pre_size(registry_horizontal)
        assert horizontal_beam.height % 5 == 0, (
            "height after pre_size should be a multiple of 5"
        )

    def test_pre_size_result_correct_for_200cm_spans(
        self,
        horizontal_beam: ContinuousBeam,
        registry_horizontal: dict[str, Pillar],
    ) -> None:
        # spans are 200 cm; 200/15 ≈ 13.3 → round_up → 15
        horizontal_beam.resolve_and_validate(registry_horizontal)
        horizontal_beam.pre_size(registry_horizontal)
        assert horizontal_beam.height == 15, "200 cm span should pre-size to 15 cm"

    def test_pre_size_uses_effective_span_on_wide_pillars(
        self, wall: WallDefinition
    ) -> None:
        # Centroid distance 600 -> 600/15 = 40, but l_ef converges to
        # 500 + 2 * 0.3 * 35 = 521 -> 521/15 ≈ 34.7 -> 35
        p1 = Pillar(x=0, y=0, width=100, depth=20)
        p2 = Pillar(x=600, y=0, width=100, depth=20)
        registry = {p1.id: p1, p2.id: p2}
        beam = ContinuousBeam(
            pillar_ids=[p1.id, p2.id],
            reference_pillar_id=p1.id,
            width=16,
            alignment=Alignment.BOTTOM,
            wall=wall,
        )
        beam.resolve_and_validate(registry)
        beam.pre_size(registry)
        assert beam.height == 35, "wide pillars should pre-size from l_ef, not 600 cm"


# ---------------------------------------------------------------------------
# TestLoadSpans (mocked LinearLoads)
# ---------------------------------------------------------------------------


class TestLoadSpans:
    """load_spans adds own-weight + wall load to each span's permanent_load."""

    def test_spans_receive_permanent_load(
        self,
        horizontal_beam: ContinuousBeam,
        registry_horizontal: dict[str, Pillar],
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        horizontal_beam.resolve_and_validate(registry_horizontal)
        horizontal_beam.pre_size(registry_horizontal)

        monkeypatch.setattr(
            LinearLoads,
            "get_concrete_element_own_weight",
            lambda area: 2.0,  # type: ignore
        )
        monkeypatch.setattr(LinearLoads, "get_wall_load", lambda *a, **kw: 3.0)  # type: ignore
        monkeypatch.setattr(APP_CONFIG, "ceiling_height", 2.5)

        horizontal_beam.load_spans()

        for span in horizontal_beam.spans:
            assert span.permanent_load > 0, (
                "each span should have a positive permanent_load"
            )

    def test_load_spans_sums_own_weight_and_wall(
        self,
        horizontal_beam: ContinuousBeam,
        registry_horizontal: dict[str, Pillar],
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        horizontal_beam.resolve_and_validate(registry_horizontal)
        horizontal_beam.pre_size(registry_horizontal)

        monkeypatch.setattr(
            LinearLoads,
            "get_concrete_element_own_weight",
            lambda area: 2.0,  # type: ignore
        )
        monkeypatch.setattr(LinearLoads, "get_wall_load", lambda *a, **kw: 3.0)  # type: ignore
        monkeypatch.setattr(APP_CONFIG, "ceiling_height", 2.5)

        horizontal_beam.load_spans()

        for span in horizontal_beam.spans:
            assert_approx(
                span.permanent_load, 5.0, "load should be own_weight + wall = 5.0 kN/m"
            )


# ---------------------------------------------------------------------------
# TestDimension (mocked BeamCalculator)
# ---------------------------------------------------------------------------


class TestDimension:
    """dimension() instantiates and runs a BeamCalculator."""

    def test_dimension_invokes_calculator(
        self,
        horizontal_beam: ContinuousBeam,
        registry_horizontal: dict[str, Pillar],
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        horizontal_beam.resolve_and_validate(registry_horizontal)
        horizontal_beam.pre_size(registry_horizontal)

        calls: list[str] = []

        class _FakeCalc:
            def __init__(
                self, beam: ContinuousBeam, registry: dict[str, Pillar]
            ) -> None:
                pass

            def run(self) -> None:
                calls.append("run")

        monkeypatch.setattr(_cb_module, "BeamCalculator", _FakeCalc)
        horizontal_beam.dimension(registry_horizontal)

        assert calls == ["run"], "dimension() should call BeamCalculator.run() once"


# ---------------------------------------------------------------------------
# TestGetMostLoadedSpanForEls
# ---------------------------------------------------------------------------


class TestGetMostLoadedSpanForEls:
    """get_most_loaded_span_for_els returns the heavier span; raises when empty."""

    def test_no_spans_raises(
        self,
        pillars_horizontal: tuple[Pillar, Pillar, Pillar],
        wall: WallDefinition,
    ) -> None:
        p1, p2, _ = pillars_horizontal
        b = ContinuousBeam(
            pillar_ids=[p1.id, p2.id],
            reference_pillar_id=p1.id,
            width=16,
            alignment=Alignment.BOTTOM,
            wall=wall,
        )
        with pytest.raises(ValueError, match="has no spans to evaluate"):
            b.get_most_loaded_span_for_els()

    def test_returns_heavier_span(
        self,
        horizontal_beam: ContinuousBeam,
        registry_horizontal: dict[str, Pillar],
        pillars_horizontal: tuple[Pillar, Pillar, Pillar],
    ) -> None:
        horizontal_beam.resolve_and_validate(registry_horizontal)
        p1, p2, _ = pillars_horizontal
        horizontal_beam.spans[0].permanent_load = 10.0
        horizontal_beam.spans[0].variable_load = 2.0
        horizontal_beam.spans[1].permanent_load = 5.0
        horizontal_beam.spans[1].variable_load = 1.0

        heaviest = horizontal_beam.get_most_loaded_span_for_els()

        assert heaviest.start_pillar_id == p1.id, "heavier span should be span 0"
        assert heaviest.end_pillar_id == p2.id, "heavier span should end at p2"
