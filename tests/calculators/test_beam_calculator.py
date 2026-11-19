"""Unit tests for src/calculators/beam_calculator.py — BeamCalculator.

Isolated branch tests use SimpleNamespace doubles and monkeypatching.
The integration test exercises the real end-to-end pipeline on a
conservative 20×60 C25/CA50 single-span beam.
"""

import math
import types
from itertools import pairwise

import pytest

from src.analysis.model import BeamSupport, DistributedLoad
from src.analysis.solver import analyse_beam
from src.calculators import beam_calculator
from src.calculators.beam_calculator import BeamCalculator
from src.checkers.beam_deformation_checker import BeamDeformationChecker
from src.config import APP_CONFIG
from src.loading.forces import LOAD_FACTOR
from src.pavement_elements.geometry_utils import Axis
from src.pavement_elements.pillar import Pillar
from src.properties.concrete import Concrete
from src.properties.steel import Steel
from src.reinforcement.stirrups import Stirrups, StirrupZone
from src.structural_elements.rectangular_beam import RectangularBeam
from tests.helpers import assert_approx

# ---------------------------------------------------------------------------
# Span / beam stub helpers
# ---------------------------------------------------------------------------

# span length used throughout isolated tests (cm)
_SPAN_LENGTH_CM = 500.0


def _make_span_stub(
    permanent_load: float = 10.0,
    variable_load: float = 5.0,
    length_cm: float = _SPAN_LENGTH_CM,
) -> types.SimpleNamespace:
    """Return a minimal Span stub whose length getters ignore the registry.

    ``set_stirrups`` stores the stirrups on the stub, like ``Span.set_stirrups``.
    """
    span = types.SimpleNamespace(
        permanent_load=permanent_load,
        variable_load=variable_load,
        psi_2=0.3,
        start_pillar_id="P1",
        end_pillar_id="P2",
        get_length=lambda registry, _l=length_cm: _l,  # pyright: ignore[reportUnknownLambdaType]
        get_effective_length=lambda registry, _l=length_cm: _l,  # pyright: ignore[reportUnknownLambdaType]
    )

    def set_stirrups(stirrups: Stirrups) -> None:
        span.stirrups = stirrups

    span.set_stirrups = set_stirrups
    return span


def _make_beam_stub(
    spans: list[types.SimpleNamespace] | None = None,
    beam_id: str = "V1",
    width: float = 20.0,
    height: float = 60.0,
    axis: Axis = Axis.X,
) -> types.SimpleNamespace:
    """Return a minimal ContinuousBeam stub with one default span."""
    if spans is None:
        spans = [_make_span_stub()]
    return types.SimpleNamespace(
        id=beam_id,
        width=width,
        height=height,
        spans=spans,
        axis=axis,
        reinforcement=[],
        get_most_loaded_span_for_els=lambda: spans[0],
    )


def _make_calculator_stub(
    position: float, tensioned_area: float, compressed_area: float = 0.0
) -> types.SimpleNamespace:
    """Return a RebarCalculator stub with chosen tensioned/compressed areas (cm²)."""
    return types.SimpleNamespace(
        position=position,
        tensioned_reinforcement=types.SimpleNamespace(area=tensioned_area),
        compressed_reinforcement=types.SimpleNamespace(area=compressed_area),
        total_area=tensioned_area + compressed_area,
    )


def _make_registry(widths: dict[str, float] | None = None) -> dict[str, Pillar]:
    """Return 20x30 cm pillars keyed by the span stubs' pillar ids.

    Args:
        widths: Width (x extent, cm) per pillar id, replacing the default 20 cm; unknown ids add pillars.
    """
    widths = {"P1": 20.0, "P2": 20.0, **(widths or {})}
    return {
        pillar_id: Pillar(x=0.0, y=0.0, width=width, depth=30.0, id=pillar_id)
        for pillar_id, width in widths.items()
    }


# ---------------------------------------------------------------------------
# TestLabel
# ---------------------------------------------------------------------------


class TestLabel:
    """Tests for BeamCalculator.label."""

    def test_label_equals_beam_id(self) -> None:
        """label returns beam.id (dimensionless)."""
        bc = BeamCalculator(_make_beam_stub(beam_id="V99"), {})  # type: ignore[arg-type]
        assert bc.label == "V99", "label should equal beam.id"


# ---------------------------------------------------------------------------
# TestBuildSupports
# ---------------------------------------------------------------------------


class TestBuildSupports:
    """Tests for _build_supports() — number and cumulative positions of supports."""

    def test_single_span_two_supports(self) -> None:
        """Single-span beam creates exactly 2 supports (dimensionless)."""
        span = _make_span_stub(length_cm=400.0)
        bc = BeamCalculator(_make_beam_stub(spans=[span]), _make_registry())  # type: ignore[arg-type]
        supports = bc._build_supports()  # pyright: ignore[reportPrivateUsage]
        assert len(supports) == 2, "Single span should produce exactly 2 supports"

    def test_two_spans_three_supports(self) -> None:
        """Two-span beam creates 3 supports (dimensionless)."""
        spans = [_make_span_stub(length_cm=300.0), _make_span_stub(length_cm=400.0)]
        bc = BeamCalculator(_make_beam_stub(spans=spans), _make_registry())  # type: ignore[arg-type]
        supports = bc._build_supports()  # pyright: ignore[reportPrivateUsage]
        assert len(supports) == 3, "Two spans should produce exactly 3 supports"

    def test_cumulative_positions(self) -> None:
        """Supports are placed at cumulative span-length positions (cm)."""
        spans = [_make_span_stub(length_cm=300.0), _make_span_stub(length_cm=200.0)]
        bc = BeamCalculator(_make_beam_stub(spans=spans), _make_registry())  # type: ignore[arg-type]
        supports = bc._build_supports()  # pyright: ignore[reportPrivateUsage]
        positions = [s.position for s in supports]
        assert positions[0] == 0, "First support should be at position 0 (cm)"
        assert positions[1] == 300.0, "Second support should be at 300 cm (cm)"
        assert positions[2] == 500.0, "Third support should be at 500 cm (cm)"

    def test_supports_use_pillar_stiffness(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Each support takes its pillar's rotational stiffness (kN.m/rad)."""
        monkeypatch.setattr(APP_CONFIG, "pavement_concrete", Concrete.C25)
        registry = _make_registry()
        bc = BeamCalculator(_make_beam_stub(), registry)  # type: ignore[arg-type]
        supports = bc._build_supports()  # pyright: ignore[reportPrivateUsage]
        for support, pillar_id in zip(supports, ["P1", "P2"], strict=True):
            expected = registry[pillar_id].calculate_stiffness_for_beam_supporting(
                Axis.X
            )
            assert_approx(
                support.rotational_stiffness,
                expected,
                f"Support on {pillar_id} should use the pillar stiffness (kN.m/rad)",
            )

    @staticmethod
    def _three_support_stiffnesses(
        monkeypatch: pytest.MonkeyPatch, widths: dict[str, float]
    ) -> list[float]:
        """Rotational stiffness of the supports on P1, P2 and P3 of a two-span X beam, H = 2.5 m (e/4 = 62.5 cm)."""
        monkeypatch.setattr(APP_CONFIG, "ceiling_height", 2.5)
        spans = [_make_span_stub(), _make_span_stub()]
        spans[1].start_pillar_id = "P2"
        spans[1].end_pillar_id = "P3"
        registry = _make_registry({"P3": 20.0, **widths})
        bc = BeamCalculator(_make_beam_stub(spans=spans), registry)  # type: ignore[arg-type]
        return [s.rotational_stiffness for s in bc._build_supports()]  # pyright: ignore[reportPrivateUsage]

    def test_wide_interior_pillar_is_rigid(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """b_int = 70 cm > e/4 = 62.5 cm → fixed interior support (NBR 6118 14.6.6.1-b)."""
        stiffnesses = self._three_support_stiffnesses(monkeypatch, {"P2": 70.0})
        assert math.isinf(stiffnesses[1]), "Wide interior pillar should be rigid"
        assert math.isfinite(stiffnesses[0]), "End support keeps its spring"
        assert math.isfinite(stiffnesses[2]), "End support keeps its spring"

    def test_narrow_interior_pillar_keeps_spring(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """b_int = 20 cm ≤ e/4 → the interior support keeps the pillar's spring (kN.m/rad)."""
        stiffnesses = self._three_support_stiffnesses(monkeypatch, {})
        expected = Pillar(
            x=0.0, y=0.0, width=20.0, depth=30.0
        ).calculate_stiffness_for_beam_supporting(Axis.X)
        assert_approx(
            stiffnesses[1], expected, "Narrow interior pillar keeps its spring"
        )

    def test_wide_end_pillar_keeps_spring(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """A wide pillar at a beam end stays elastic (NBR 6118 14.6.6.1-c)."""
        stiffnesses = self._three_support_stiffnesses(
            monkeypatch, {"P1": 70.0, "P3": 70.0}
        )
        assert math.isfinite(stiffnesses[0]), "Wide start pillar keeps its spring"
        assert math.isfinite(stiffnesses[2]), "Wide end pillar keeps its spring"

    def test_rigid_interior_support_uncouples_the_spans(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Each side of a rigid interior support reads its span as if fixed there alone (kN.m)."""
        monkeypatch.setattr(APP_CONFIG, "ceiling_height", 2.5)
        monkeypatch.setattr(APP_CONFIG, "pavement_concrete", Concrete.C25)
        spans = [
            _make_span_stub(length_cm=400.0),
            _make_span_stub(length_cm=600.0),
        ]
        spans[1].start_pillar_id = "P2"
        spans[1].end_pillar_id = "P3"
        registry = _make_registry({"P2": 70.0, "P3": 20.0})
        bc = BeamCalculator(_make_beam_stub(spans=spans), registry)  # type: ignore[arg-type]
        supports = bc._build_supports()  # pyright: ignore[reportPrivateUsage]
        load = spans[0].permanent_load + spans[0].variable_load  # kN/m
        analysis = analyse_beam(
            bc._build_structural_beam(),  # pyright: ignore[reportPrivateUsage]
            supports,
            bc._build_loads(),  # pyright: ignore[reportPrivateUsage]
        )

        def alone(length: float, left: float, right: float) -> float:
            """Moment at the rigid end of one span solved alone (kN.m)."""
            beam = RectangularBeam(length, 20.0, 60.0, Steel.CA50)
            single = analyse_beam(
                beam,
                [BeamSupport(0.0, left), BeamSupport(length, right)],
                [DistributedLoad(0.0, length, load)],
            )
            return single.bending_moment(length if math.isinf(right) else 0.0)

        assert_approx(
            analysis.bending_moment(400.0),
            alone(400.0, supports[0].rotational_stiffness, math.inf),
            "Left side should match the 4 m span fixed at P2",
            abs_tol=1e-3,
        )
        assert_approx(
            analysis.bending_moment(400.0, from_right=True),
            alone(600.0, math.inf, supports[2].rotational_stiffness),
            "Right side should match the 6 m span fixed at P2",
            abs_tol=1e-3,
        )


# ---------------------------------------------------------------------------
# TestBuildLoads
# ---------------------------------------------------------------------------


class TestBuildLoads:
    """Tests for _build_loads() — one DistributedLoad per span."""

    def test_one_load_per_span(self) -> None:
        """_build_loads() returns one load object per span (dimensionless)."""
        spans = [_make_span_stub(), _make_span_stub()]
        bc = BeamCalculator(_make_beam_stub(spans=spans), {})  # type: ignore[arg-type]
        loads = bc._build_loads()  # pyright: ignore[reportPrivateUsage]
        assert len(loads) == 2, "Should produce one load per span"

    def test_load_intensity_combines_permanent_and_variable(self) -> None:
        """Load intensity = permanent + variable, positive downward (kN/m)."""
        span = _make_span_stub(permanent_load=8.0, variable_load=4.0)
        bc = BeamCalculator(_make_beam_stub(spans=[span]), {})  # type: ignore[arg-type]
        loads = bc._build_loads()  # pyright: ignore[reportPrivateUsage]
        assert_approx(
            loads[0].intensity, 12.0, "Load intensity should be perm + var (kN/m)"
        )

    def test_loads_cover_consecutive_spans(self) -> None:
        """Each load spans its own span's cumulative range (cm)."""
        spans = [_make_span_stub(length_cm=300.0), _make_span_stub(length_cm=200.0)]
        bc = BeamCalculator(_make_beam_stub(spans=spans), {})  # type: ignore[arg-type]
        loads = bc._build_loads()  # pyright: ignore[reportPrivateUsage]
        ranges = [(load.start, load.end) for load in loads]
        assert ranges == [(0.0, 300.0), (300.0, 500.0)], (
            "Loads should cover [0, 300] and [300, 500] cm"
        )


# ---------------------------------------------------------------------------
# TestBuildStructuralBeam
# ---------------------------------------------------------------------------


class TestBuildStructuralBeam:
    """Tests for _build_structural_beam() — reads APP_CONFIG, builds RectangularBeam."""

    def test_builds_with_valid_config(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """_build_structural_beam() returns a RectangularBeam with correct dimensions."""
        monkeypatch.setattr(APP_CONFIG, "pavement_concrete", Concrete.C25)
        monkeypatch.setattr(APP_CONFIG, "pavement_steel", Steel.CA50)

        span = _make_span_stub(length_cm=500.0)
        bc = BeamCalculator(_make_beam_stub(spans=[span]), _make_registry())  # type: ignore[arg-type]
        beam = bc._build_structural_beam()  # pyright: ignore[reportPrivateUsage]

        from src.structural_elements.rectangular_beam import RectangularBeam

        assert isinstance(beam, RectangularBeam), (
            "_build_structural_beam should return a RectangularBeam"
        )
        assert beam.width == 20.0, "beam width should be 20 cm (cm)"
        assert beam.height == 60.0, "beam height should be 60 cm (cm)"
        assert beam.steel == Steel.CA50, "beam steel should be CA50"

    def test_supports_span_pillar_widths(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Supports sit at cumulative effective lengths, ±half the pillar width (cm)."""
        monkeypatch.setattr(APP_CONFIG, "pavement_concrete", Concrete.C25)
        monkeypatch.setattr(APP_CONFIG, "pavement_steel", Steel.CA50)

        spans = [_make_span_stub(length_cm=300.0), _make_span_stub(length_cm=200.0)]
        bc = BeamCalculator(_make_beam_stub(spans=spans), _make_registry())  # type: ignore[arg-type]
        beam = bc._build_structural_beam()  # pyright: ignore[reportPrivateUsage]

        faces = [(s.left, s.center, s.right) for s in beam.supports]
        assert faces == [
            (-10.0, 0.0, 10.0),
            (290.0, 300.0, 310.0),
            (490.0, 500.0, 510.0),
        ], "20 cm wide pillars on an X beam should give faces 10 cm from each center"


# ---------------------------------------------------------------------------
# TestInterestPoints
# ---------------------------------------------------------------------------


class TestInterestPoints:
    """Tests for _interest_points() — the analysis' extremes, split at interior supports."""

    def test_returns_extreme_per_segment(self) -> None:
        """_interest_points() returns the analysis' per-segment extremes (cm, kN.m)."""
        analysis = types.SimpleNamespace(
            moment_extremes_per_segment=lambda: [(250.0, 42.0), (500.0, -30.0)],
        )
        bc = BeamCalculator(_make_beam_stub(), {})  # type: ignore[arg-type]
        points = bc._interest_points(analysis)  # pyright: ignore[reportPrivateUsage, reportArgumentType]

        assert points == [(250.0, 42.0), (500.0, -30.0)], (
            "_interest_points should return the per-segment extremes"
        )

    def test_splits_interior_support_point(self) -> None:
        """A point on an interior support becomes one point 0.01 cm to each side, each with its side's moment (cm, kN.m)."""
        analysis = types.SimpleNamespace(
            moment_extremes_per_segment=lambda: [(300.0, -60.0)],
            bending_moment=lambda position, from_right=False: (  # pyright: ignore[reportUnknownLambdaType]
                -50.0 if from_right else -60.0
            ),
        )
        spans = [_make_span_stub(length_cm=300.0), _make_span_stub(length_cm=200.0)]
        bc = BeamCalculator(_make_beam_stub(spans=spans), {})  # type: ignore[arg-type]

        points = bc._interest_points(analysis)  # pyright: ignore[reportPrivateUsage, reportArgumentType]

        assert len(points) == 2, "the support point should be split in two"
        assert_approx(
            points[0][0], 299.99, "left point 0.01 cm before the support (cm)"
        )
        assert_approx(
            points[1][0], 300.01, "right point 0.01 cm after the support (cm)"
        )
        assert points[0][1] == -60.0, "left point reads the moment left of the support"
        assert points[1][1] == -50.0, (
            "right point reads the moment right of the support, past the spring's jump"
        )

    def test_keeps_beam_end_and_midspan_points(self) -> None:
        """Points at the beam ends or inside a span are not split (cm, kN.m)."""
        extremes = [(0.0, -20.0), (150.0, 40.0), (420.0, 25.0), (500.0, -15.0)]
        analysis = types.SimpleNamespace(moment_extremes_per_segment=lambda: extremes)
        spans = [_make_span_stub(length_cm=300.0), _make_span_stub(length_cm=200.0)]
        bc = BeamCalculator(_make_beam_stub(spans=spans), {})  # type: ignore[arg-type]

        points = bc._interest_points(analysis)  # pyright: ignore[reportPrivateUsage, reportArgumentType]

        assert points == extremes, "end and midspan points should be kept as they are"


# ---------------------------------------------------------------------------
# TestRoundSupportMoments
# ---------------------------------------------------------------------------


class TestRoundSupportMoments:
    """Tests for _round_support_moments() — NBR 6118:2026 14.6.3, ΔM = R·t/8."""

    @staticmethod
    def _round(
        points: list[tuple[float, float]],
        reaction: float = 100.0,
        interior_stiffness: float = 1000.0,
    ) -> list[tuple[float, float]]:
        """Run the rounding on supports at 0, 300 and 500 cm, 20 cm wide (kN reaction).

        Args:
            interior_stiffness: Rotational stiffness of the support at 300 cm (kN.m/rad); the end supports get 1000 kN.m/rad.
        """
        analysis = types.SimpleNamespace(reaction=lambda position: reaction)  # pyright: ignore[reportUnknownLambdaType]
        centers = (0.0, 300.0, 500.0)
        geometry = [
            types.SimpleNamespace(center=c, left=c - 10.0, right=c + 10.0)
            for c in centers
        ]
        structural_beam = types.SimpleNamespace(supports=geometry)
        supports = [
            BeamSupport(0.0, 1000.0),
            BeamSupport(300.0, interior_stiffness),
            BeamSupport(500.0, 1000.0),
        ]
        bc = BeamCalculator(_make_beam_stub(), {})  # type: ignore[arg-type]
        return bc._round_support_moments(points, analysis, structural_beam, supports)  # pyright: ignore[reportPrivateUsage, reportArgumentType]

    def test_rigid_support_not_rounded(self) -> None:
        """A rigid interior support keeps the fixed-end moment (NBR 6118 14.6.6.1-b)."""
        points = [(299.99, -60.0), (300.01, -50.0)]

        assert self._round(points, interior_stiffness=math.inf) == points, (
            "rigid support moments should not be rounded"
        )

    def test_interior_support_reduced_on_both_sides(self) -> None:
        """R = 100 kN, t = 20 cm → ΔM = 2.5 kN.m on each side of the split point."""
        rounded = self._round([(299.99, -60.0), (300.01, -50.0)])

        assert_approx(rounded[0][1], -57.5, "left side moment (kN.m)")
        assert_approx(rounded[1][1], -47.5, "right side moment (kN.m)")
        assert rounded[0][0] == 299.99, "positions are kept"

    def test_reduction_never_changes_sign(self) -> None:
        """A ΔM larger than |M| leaves zero, not a positive moment (kN.m)."""
        rounded = self._round([(300.0, -1.0)])

        assert rounded == [(300.0, 0.0)], "rounded moment should stop at zero"

    def test_positive_and_span_points_unchanged(self) -> None:
        """Sagging moments, even on a support, and points inside spans are kept."""
        points = [(150.0, 40.0), (300.0, 5.0), (200.0, -10.0)]

        assert self._round(points) == points, "only hogging moments on supports change"

    def test_end_support_reduced(self) -> None:
        """A hogging moment at a beam end support is rounded too (kN.m)."""
        rounded = self._round([(500.0, -20.0)])

        assert_approx(rounded[0][1], -17.5, "end support moment (kN.m)")


# ---------------------------------------------------------------------------
# TestSpanRanges
# ---------------------------------------------------------------------------


class TestSpanRanges:
    """Tests for _span_ranges() — each span with its start and end positions (cm)."""

    def test_cumulative_ranges(self) -> None:
        """Spans follow each other along the beam (cm)."""
        first = _make_span_stub(length_cm=300.0)
        second = _make_span_stub(length_cm=200.0)
        bc = BeamCalculator(_make_beam_stub(spans=[first, second]), {})  # type: ignore[arg-type]

        ranges = bc._span_ranges()  # pyright: ignore[reportPrivateUsage]

        assert ranges == [(first, 0.0, 300.0), (second, 300.0, 500.0)], (
            "each span should start where the previous one ends (cm)"
        )


# ---------------------------------------------------------------------------
# TestSpanAt
# ---------------------------------------------------------------------------


class TestSpanAt:
    """Tests for _span_at() — maps a position (cm) to its owning span."""

    def test_maps_position_to_correct_span(self) -> None:
        """_span_at() returns the span whose cumulative range contains the position (cm)."""
        first = _make_span_stub(length_cm=300.0)
        second = _make_span_stub(length_cm=200.0)
        bc = BeamCalculator(_make_beam_stub(spans=[first, second]), {})  # type: ignore[arg-type]

        assert bc._span_at(150.0) is first, "position 150 cm is in the first span"  # pyright: ignore[reportPrivateUsage]
        assert bc._span_at(300.0) is first, "position 300 cm is the first span's edge"  # pyright: ignore[reportPrivateUsage]
        assert bc._span_at(450.0) is second, "position 450 cm is in the second span"  # pyright: ignore[reportPrivateUsage]

    def test_position_past_end_returns_last_span(self) -> None:
        """_span_at() returns the last span for a position at/after the beam end (cm)."""
        first = _make_span_stub(length_cm=300.0)
        second = _make_span_stub(length_cm=200.0)
        bc = BeamCalculator(_make_beam_stub(spans=[first, second]), {})  # type: ignore[arg-type]

        assert bc._span_at(500.0) is second, "end position maps to the last span"  # pyright: ignore[reportPrivateUsage]


# ---------------------------------------------------------------------------
# TestVerifyDeformation
# ---------------------------------------------------------------------------


class TestVerifyDeformation:
    """Tests for _verify_deformation() — calls BeamDeformationChecker."""

    def _make_structural_beam_stub(self) -> types.SimpleNamespace:
        """Build a structural beam (section) stub compatible with _verify_deformation."""
        return types.SimpleNamespace(width=20.0, height=60.0)

    def _make_analysis_stub(self) -> types.SimpleNamespace:
        """Build a BeamAnalysis stub with canned moment (kN.m) and deflection (cm)."""
        return types.SimpleNamespace(
            bending_moment=lambda position: 150.0,  # pyright: ignore[reportUnknownLambdaType]
            deflection=lambda position: 0.1,  # pyright: ignore[reportUnknownLambdaType]
        )

    def _make_rebar_calculator_stub(self) -> types.SimpleNamespace:
        """Build a rebar_calculator stub with area attrs."""
        tensioned = types.SimpleNamespace(area=18.5)
        compressed = types.SimpleNamespace(area=4.6)
        return types.SimpleNamespace(
            d=56.0,
            d_compressed=4.0,
            tensioned_reinforcement=tensioned,
            compressed_reinforcement=compressed,
        )

    def test_passes_silently_when_deformation_ok(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """_verify_deformation() returns None when checker.verify returns True."""
        monkeypatch.setattr(BeamDeformationChecker, "verify", lambda self, h: True)  # type: ignore

        span = _make_span_stub()
        bc = BeamCalculator(_make_beam_stub(spans=[span]), {})  # type: ignore[arg-type]

        result = bc._verify_deformation(  # type: ignore[arg-type]
            self._make_structural_beam_stub(),  # type: ignore[arg-type]
            self._make_analysis_stub(),  # type: ignore[arg-type]
            self._make_rebar_calculator_stub(),  # type: ignore[arg-type]
            250.0,
        )
        assert result is None, "_verify_deformation should return None on success"

    def test_raises_when_deformation_exceeds(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """_verify_deformation() raises ValueError when checker.verify returns False."""
        # Make immediate_deflection and long_term_deflection available for the error message
        monkeypatch.setattr(BeamDeformationChecker, "verify", lambda self, h: False)  # type: ignore
        monkeypatch.setattr(
            BeamDeformationChecker,
            "immediate_deflection",
            property(lambda self: 5.0),
        )
        monkeypatch.setattr(
            BeamDeformationChecker,
            "long_term_deflection",
            property(lambda self: 15.0),
        )
        monkeypatch.setattr(
            BeamDeformationChecker,
            "acceptable_deflection",
            property(lambda self: 1.0),
        )

        span = _make_span_stub()
        bc = BeamCalculator(_make_beam_stub(spans=[span]), {})  # type: ignore[arg-type]
        structural_beam = self._make_structural_beam_stub()
        rebar_calculator = self._make_rebar_calculator_stub()
        with pytest.raises(ValueError, match="Deformation exceeds"):
            bc._verify_deformation(  # type: ignore[arg-type]
                structural_beam,  # type: ignore[arg-type]
                self._make_analysis_stub(),  # type: ignore[arg-type]
                rebar_calculator,  # type: ignore[arg-type]
                250.0,
            )


# ---------------------------------------------------------------------------
# TestRunPropagatesErrors
# ---------------------------------------------------------------------------


class TestRunPropagatesErrors:
    """run() never skips an interest point that cannot be dimensioned."""

    def test_dimensioning_error_is_raised(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """A ValueError from dimensioning propagates out of run()."""
        monkeypatch.setattr(APP_CONFIG, "pavement_concrete", Concrete.C25)
        monkeypatch.setattr(APP_CONFIG, "pavement_steel", Steel.CA50)

        def failing_calculate(*args: object, **kwargs: object) -> None:
            raise ValueError("boom")

        monkeypatch.setattr(
            BeamCalculator, "_build_rebar_calculator", failing_calculate
        )
        bc = BeamCalculator(_make_beam_stub(), _make_registry())  # type: ignore[arg-type]
        with pytest.raises(ValueError, match="boom"):
            bc.run()


# ---------------------------------------------------------------------------
# TestGetInteriorSupports
# ---------------------------------------------------------------------------


class TestGetInteriorSupports:
    """Tests for _get_interior_supports() — supports between spans (cm)."""

    def test_two_spans_have_one_interior_support(self) -> None:
        """The support between two spans sits at the first span's end (cm)."""
        spans = [_make_span_stub(length_cm=300.0), _make_span_stub(length_cm=200.0)]
        bc = BeamCalculator(_make_beam_stub(spans=spans), {})  # type: ignore[arg-type]

        assert bc._get_interior_supports() == [300.0], (  # pyright: ignore[reportPrivateUsage]
            "the only interior support is at 300 cm"
        )

    def test_single_span_has_none(self) -> None:
        """A single span has only end supports."""
        bc = BeamCalculator(_make_beam_stub(), {})  # type: ignore[arg-type]

        assert bc._get_interior_supports() == [], (  # pyright: ignore[reportPrivateUsage]
            "a single span has no interior support"
        )


# ---------------------------------------------------------------------------
# TestKeepGoverningSupportResults
# ---------------------------------------------------------------------------


class TestKeepGoverningSupportResults:
    """Tests for _keep_governing_support_results() — one result per interior support."""

    @staticmethod
    def _make_calculator() -> BeamCalculator:
        """Build a BeamCalculator over two spans (300 + 200 cm)."""
        spans = [_make_span_stub(length_cm=300.0), _make_span_stub(length_cm=200.0)]
        return BeamCalculator(_make_beam_stub(spans=spans), {})  # type: ignore[arg-type]

    def test_keeps_greatest_total_area(self) -> None:
        """The side with the greater tensioned + compressed area is kept (cm²)."""
        left = _make_calculator_stub(299.99, tensioned_area=5.0)
        right = _make_calculator_stub(300.01, tensioned_area=4.0, compressed_area=2.0)
        results = [(299.99, left), (300.01, right)]

        kept = self._make_calculator()._keep_governing_support_results(results)  # type: ignore[arg-type]  # pyright: ignore[reportPrivateUsage]

        assert kept == [(300.01, right)], (
            "4 + 2 cm² on the right beats 5 cm² on the left"
        )

    def test_tie_keeps_left_side(self) -> None:
        """Equal total areas keep the left side (cm²)."""
        left = _make_calculator_stub(299.99, tensioned_area=5.0)
        right = _make_calculator_stub(300.01, tensioned_area=5.0)
        results = [(299.99, left), (300.01, right)]

        kept = self._make_calculator()._keep_governing_support_results(results)  # type: ignore[arg-type]  # pyright: ignore[reportPrivateUsage]

        assert kept == [(299.99, left)], "a tie should keep the left side"

    def test_other_results_pass_through(self) -> None:
        """Beam-end and midspan results are kept as they are, in order."""
        results = [
            (0.0, _make_calculator_stub(0.0, tensioned_area=2.0)),
            (150.0, _make_calculator_stub(150.0, tensioned_area=4.0)),
            (420.0, _make_calculator_stub(420.0, tensioned_area=3.0)),
            (500.0, _make_calculator_stub(500.0, tensioned_area=2.0)),
        ]

        kept = self._make_calculator()._keep_governing_support_results(results)  # type: ignore[arg-type]  # pyright: ignore[reportPrivateUsage]

        assert kept == results, "results away from interior supports are unchanged"


# ---------------------------------------------------------------------------
# TestRunBySpan
# ---------------------------------------------------------------------------


def _no_outer_supports(*args: object) -> list[object]:
    """Skip the end support step, which needs real calculators"""
    return []


class TestRunBySpan:
    """run() coordinates each span's stirrups with the interest points inside it."""

    def test_coordinates_each_span_with_its_points(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Each span is coordinated once, and an interior-support point reaches both spans (cm)."""
        monkeypatch.setattr(APP_CONFIG, "pavement_concrete", Concrete.C25)
        monkeypatch.setattr(APP_CONFIG, "pavement_steel", Steel.CA50)
        analysis = types.SimpleNamespace(
            moment_extremes_per_segment=lambda: [
                (150.0, 40.0),
                (300.0, -60.0),
                (420.0, 25.0),
            ],
            shear_force=lambda position: 50.0,  # pyright: ignore[reportUnknownLambdaType]
            moment_zeros=list[float],
            positions_for_moment=list[float],
            bending_moment=lambda position, from_right=False: 0.0,  # pyright: ignore[reportUnknownLambdaType]
        )

        def analyse_beam(*args: object) -> types.SimpleNamespace:
            return analysis

        def build_rebar_calculator(
            self: BeamCalculator,
            structural_beam: object,
            moment: float,
            position: float,
            moment_zeros: tuple[float, ...],
            support_moments: tuple[float, ...],
            moment_positions: object,
        ) -> types.SimpleNamespace:
            # the support's right side (300.01 cm) needs more steel than its left side
            return _make_calculator_stub(
                position, tensioned_area=5.0 if position > 300.0 else 4.0
            )

        stored: list[float] = []

        def store_reinforcement(
            self: BeamCalculator, calculator: types.SimpleNamespace
        ) -> None:
            stored.append(calculator.position)

        def verify_deformation(*args: object) -> None:
            return None

        coordinated: list[list[float]] = []

        def coordinate_span(
            calculators: list[types.SimpleNamespace], stirrups: object
        ) -> None:
            coordinated.append([calculator.position for calculator in calculators])

        distributed: list[tuple[object, float, float]] = []

        def distribute(
            self: Stirrups, analysis: object, start: float, end: float
        ) -> None:
            distributed.append((analysis, start, end))

        monkeypatch.setattr(beam_calculator, "analyse_beam", analyse_beam)
        monkeypatch.setattr(
            BeamCalculator, "_build_rebar_calculator", build_rebar_calculator
        )
        monkeypatch.setattr(BeamCalculator, "_store_reinforcement", store_reinforcement)
        monkeypatch.setattr(BeamCalculator, "_verify_deformation", verify_deformation)
        monkeypatch.setattr(beam_calculator, "coordinate_span", coordinate_span)
        monkeypatch.setattr(BeamCalculator, "_outer_supports", _no_outer_supports)
        monkeypatch.setattr(Stirrups, "distribute", distribute)
        spans = [_make_span_stub(length_cm=300.0), _make_span_stub(length_cm=200.0)]
        beam = _make_beam_stub(spans=spans)
        bc = BeamCalculator(beam, _make_registry())  # type: ignore[arg-type]

        bc.run()

        assert beam.analysis is analysis, "run() should keep the beam's analysis"
        kept = [calculator.position for calculator in beam.rebar_calculators]
        for actual, expected in zip(kept, [150.0, 300.01, 420.0], strict=True):
            assert_approx(
                actual, expected, "only governing calculators kept, left to right (cm)"
            )
        assert len(coordinated) == 2, "each span should be coordinated once"
        for actual, expected in zip(coordinated[0], [150.0, 299.99], strict=True):
            assert_approx(
                actual, expected, "first span: midspan point and support's left (cm)"
            )
        for actual, expected in zip(coordinated[1], [300.01, 420.0], strict=True):
            assert_approx(
                actual, expected, "second span: support's right and midspan point (cm)"
            )
        assert distributed == [(analysis, 0.0, 300.0), (analysis, 300.0, 500.0)], (
            "each span's stirrups should be distributed over its own range (cm)"
        )
        assert len(stored) == 3, "the support should be stored once"
        for actual, expected in zip(stored, [150.0, 300.01, 420.0], strict=True):
            assert_approx(
                actual, expected, "support stored from its governing (right) side (cm)"
            )

    def test_span_without_points_uses_its_greatest_moment(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """A span without interest points is dimensioned at its greatest |M|, searched 0.01 cm inside its ends (cm, kN.m)."""
        monkeypatch.setattr(APP_CONFIG, "pavement_concrete", Concrete.C25)
        monkeypatch.setattr(APP_CONFIG, "pavement_steel", Steel.CA50)
        searched: list[tuple[float, float]] = []

        def moment_extreme_in_range(start: float, end: float) -> tuple[float, float]:
            searched.append((start, end))
            return start, -25.0

        analysis = types.SimpleNamespace(
            moment_extremes_per_segment=lambda: [(150.0, 40.0)],
            moment_extreme_in_range=moment_extreme_in_range,
            reaction=lambda position: 0.0,  # pyright: ignore[reportUnknownLambdaType]
            shear_force=lambda position: 50.0,  # pyright: ignore[reportUnknownLambdaType]
            moment_zeros=list[float],
            positions_for_moment=list[float],
            bending_moment=lambda position, from_right=False: 0.0,  # pyright: ignore[reportUnknownLambdaType]
        )

        def analyse_beam(*args: object) -> types.SimpleNamespace:
            return analysis

        built: list[tuple[float, float]] = []

        def build_rebar_calculator(
            self: BeamCalculator,
            structural_beam: object,
            moment: float,
            position: float,
            moment_zeros: tuple[float, ...],
            support_moments: tuple[float, ...],
            moment_positions: object,
        ) -> types.SimpleNamespace:
            built.append((position, moment))
            return _make_calculator_stub(position, tensioned_area=4.0)

        def store_reinforcement(
            self: BeamCalculator, calculator: types.SimpleNamespace
        ) -> None:
            return None

        def verify_deformation(*args: object) -> None:
            return None

        coordinated: list[list[float]] = []

        def coordinate_span(
            calculators: list[types.SimpleNamespace], stirrups: object
        ) -> None:
            coordinated.append([calculator.position for calculator in calculators])

        monkeypatch.setattr(beam_calculator, "analyse_beam", analyse_beam)
        monkeypatch.setattr(
            BeamCalculator, "_build_rebar_calculator", build_rebar_calculator
        )
        monkeypatch.setattr(BeamCalculator, "_store_reinforcement", store_reinforcement)
        monkeypatch.setattr(BeamCalculator, "_verify_deformation", verify_deformation)
        monkeypatch.setattr(beam_calculator, "coordinate_span", coordinate_span)
        monkeypatch.setattr(BeamCalculator, "_outer_supports", _no_outer_supports)
        monkeypatch.setattr(Stirrups, "distribute", verify_deformation)
        spans = [_make_span_stub(length_cm=300.0), _make_span_stub(length_cm=200.0)]
        bc = BeamCalculator(_make_beam_stub(spans=spans), _make_registry())  # type: ignore[arg-type]

        bc.run()

        assert len(coordinated) == 2, "the span without points should be coordinated"
        assert len(searched) == 1, "only the span without points should be searched"
        assert_approx(searched[0][0], 300.01, "search starts inside the span (cm)")
        assert_approx(searched[0][1], 499.99, "search ends inside the span (cm)")
        assert len(coordinated[1]) == 1, "the span gets a single interest point"
        assert_approx(
            coordinated[1][0], 300.01, "point at the span's greatest moment (cm)"
        )
        assert built[-1][1] == -25.0, "the point keeps the moment's sign (kN.m)"

    def test_passes_support_moments_to_calculators(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Each calculator gets the moment at every support center as its span sees it, left to right (kN.m)."""
        monkeypatch.setattr(APP_CONFIG, "pavement_concrete", Concrete.C25)
        monkeypatch.setattr(APP_CONFIG, "pavement_steel", Steel.CA50)
        left_moments = {0.0: -10.0, 300.0: -60.0, 500.0: -5.0}  # kN.m
        right_moments = {0.0: -10.0, 300.0: -50.0, 500.0: -5.0}  # kN.m, jump at 300

        def bending_moment(position: float, from_right: bool = False) -> float:
            return (right_moments if from_right else left_moments)[position]

        analysis = types.SimpleNamespace(
            moment_extremes_per_segment=lambda: [(150.0, 40.0), (420.0, 25.0)],
            shear_force=lambda position: 50.0,  # pyright: ignore[reportUnknownLambdaType]
            moment_zeros=list[float],
            positions_for_moment=list[float],
            bending_moment=bending_moment,
        )

        def analyse_beam(*args: object) -> types.SimpleNamespace:
            return analysis

        received: list[tuple[float, ...]] = []

        def build_rebar_calculator(
            self: BeamCalculator,
            structural_beam: object,
            moment: float,
            position: float,
            moment_zeros: tuple[float, ...],
            support_moments: tuple[float, ...],
            moment_positions: object,
        ) -> types.SimpleNamespace:
            received.append(support_moments)
            return _make_calculator_stub(position, tensioned_area=4.0)

        def do_nothing(*args: object) -> None:
            return None

        monkeypatch.setattr(beam_calculator, "analyse_beam", analyse_beam)
        monkeypatch.setattr(
            BeamCalculator, "_build_rebar_calculator", build_rebar_calculator
        )
        monkeypatch.setattr(BeamCalculator, "_store_reinforcement", do_nothing)
        monkeypatch.setattr(BeamCalculator, "_verify_deformation", do_nothing)
        monkeypatch.setattr(beam_calculator, "coordinate_span", do_nothing)
        monkeypatch.setattr(BeamCalculator, "_outer_supports", _no_outer_supports)
        monkeypatch.setattr(Stirrups, "distribute", do_nothing)
        spans = [_make_span_stub(length_cm=300.0), _make_span_stub(length_cm=200.0)]
        bc = BeamCalculator(_make_beam_stub(spans=spans), _make_registry())  # type: ignore[arg-type]

        bc.run()

        assert received == [(-10.0, -60.0, -5.0), (-10.0, -50.0, -5.0)], (
            "each span's calculators should get the moments on the sides facing the span (kN.m)"
        )


# ---------------------------------------------------------------------------
# TestRunIntegration — one conservative real end-to-end run
# ---------------------------------------------------------------------------


class TestRunIntegration:
    """Integration test: BeamCalculator.run() on a conservative real beam.

    Uses a SimpleNamespace beam stub wired to a pre-resolved single span
    (500 cm, 15 kN/m permanent load, 5 kN/m variable load) so that the
    anaStruct solver, RebarCalculator convergence loop, and
    BeamDeformationChecker all execute against real objects — no mocking.

    The beam is 20×60 cm, C25/CA50, deliberately under-loaded so that both
    the strut check and the deformation check pass on the first iteration.
    """

    def test_run_end_to_end_single_span_beam(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """run() completes without raising for a modest single-span 20×60 C25/CA50 beam.

        Integration test — transitively covers _build_supports, _build_loads,
        _build_structural_beam, _interest_points, _build_rebar_calculator,
        coordinate_span (stirrup ↔ rebar convergence), _store_reinforcement, and _verify_deformation (pass branch).
        """
        monkeypatch.setattr(APP_CONFIG, "pavement_concrete", Concrete.C25)
        monkeypatch.setattr(APP_CONFIG, "pavement_steel", Steel.CA50)

        # Single 500 cm span with moderate loads (kN/m)
        span = _make_span_stub(permanent_load=15.0, variable_load=5.0, length_cm=500.0)
        beam_stub = _make_beam_stub(spans=[span], beam_id="V_integration")

        bc = BeamCalculator(beam_stub, _make_registry())  # type: ignore[arg-type]
        # Must complete without raising any exception
        bc.run()

        assert beam_stub.reinforcement, (
            "run() should populate the beam's reinforcement list"
        )

    def test_run_keeps_results_for_reading(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """run() keeps the analysis, the governing calculators and each span's Vk (kN)."""
        monkeypatch.setattr(APP_CONFIG, "pavement_concrete", Concrete.C25)
        monkeypatch.setattr(APP_CONFIG, "pavement_steel", Steel.CA50)
        span = _make_span_stub(permanent_load=15.0, variable_load=5.0, length_cm=500.0)
        beam_stub = _make_beam_stub(spans=[span], beam_id="V_integration")

        BeamCalculator(beam_stub, _make_registry()).run()  # type: ignore[arg-type]

        assert beam_stub.analysis is not None, "run() should keep the analysis"
        assert beam_stub.rebar_calculators, "run() should keep the calculators"
        for calculator in beam_stub.rebar_calculators:
            assert calculator.tensioned_reinforcement in beam_stub.reinforcement, (
                "each kept calculator's reinforcement should be stored on the beam"
            )
        # uniform 20 kN/m on 500 cm: |V| at the ends ≈ qL/2 = 50 kN
        assert_approx(
            span.characteristic_shear_force,
            50.0,
            "span Vk should be the greatest |V| inside the span (kN)",
            abs_tol=0.5,
        )
        assert_approx(
            span.characteristic_shear_force * LOAD_FACTOR,
            span.stirrups.calculator.design_shear_force,
            "Vsd of the stirrups should be Vk times the load factor (kN)",
        )

    def test_run_scales_stirrups_along_span(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """A short, heavily loaded span gets denser stirrups at both ends and s_max in the middle (cm).

        300 cm span, 80 + 40 kN/m: V_k = 180 kN at the ends, so V_Sd = 252 kN exceeds the threshold shear force of the middle spacing near the supports.
        """
        monkeypatch.setattr(APP_CONFIG, "pavement_concrete", Concrete.C25)
        monkeypatch.setattr(APP_CONFIG, "pavement_steel", Steel.CA50)
        span = _make_span_stub(permanent_load=80.0, variable_load=40.0, length_cm=300.0)
        beam_stub = _make_beam_stub(spans=[span], beam_id="V_scaled")

        BeamCalculator(beam_stub, _make_registry()).run()  # type: ignore[arg-type]

        stirrups = span.stirrups
        zones: list[StirrupZone] = stirrups.zones
        assert [zone.spacing for zone in zones] == [
            stirrups.spacing,
            stirrups.middle_spacing,
            stirrups.spacing,
        ], "edges should keep the chosen spacing and the middle use the larger one"
        assert stirrups.middle_spacing > stirrups.spacing, (
            "the middle spacing should be larger than the edge spacing (cm)"
        )
        assert zones[0].start == 0.0, "the first zone should start at the span start"
        assert zones[-1].end == 300.0, "the last zone should end at the span end"
        for previous, current in pairwise(zones):
            assert previous.end == current.start, "zones should leave no gaps"
        assert_approx(
            zones[0].end - zones[0].start,
            zones[2].end - zones[2].start,
            "a symmetric span should get equal edge zones (cm)",
            abs_tol=1e-3,
        )
        # V_k(x) = 180 - 1.2 x reaches V_lim / 1.4 at the left zone's end
        assert_approx(
            zones[0].end,
            (180.0 - stirrups.threshold_shear_force / LOAD_FACTOR) / 1.2,
            "the left zone should end where |V_Sd| drops to the threshold (cm)",
            abs_tol=0.05,
        )
