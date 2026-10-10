"""Unit tests for src/calculators/beam_calculator.py — BeamCalculator.

Isolated branch tests use SimpleNamespace doubles and monkeypatching.
The integration test exercises the real end-to-end pipeline on a
conservative 20×60 C25/CA50 single-span beam.
"""

import types

import pytest

from src.calculators import beam_calculator
from src.calculators.beam_calculator import BeamCalculator
from src.checkers.beam_deformation_checker import BeamDeformationChecker
from src.config import APP_CONFIG
from src.pavement_elements.geometry_utils import Axis
from src.pavement_elements.pillar import Pillar
from src.properties.concrete import Concrete
from src.properties.steel import Steel
from src.reinforcement.stirrups import Stirrups
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


def _make_registry() -> dict[str, Pillar]:
    """Return 20x30 cm pillars keyed by the span stubs' pillar ids."""
    return {
        "P1": Pillar(x=0.0, y=0.0, width=20.0, depth=30.0),
        "P2": Pillar(x=500.0, y=0.0, width=20.0, depth=30.0),
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
                Axis.X, Concrete.C25
            )
            assert_approx(
                support.rotational_stiffness,
                expected,
                f"Support on {pillar_id} should use the pillar stiffness (kN.m/rad)",
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
        bc = BeamCalculator(_make_beam_stub(spans=[span]), {})  # type: ignore[arg-type]
        beam = bc._build_structural_beam()  # pyright: ignore[reportPrivateUsage]

        from src.structural_elements.rectangular_beam import RectangularBeam

        assert isinstance(beam, RectangularBeam), (
            "_build_structural_beam should return a RectangularBeam"
        )
        assert beam.width == 20.0, "beam width should be 20 cm (cm)"
        assert beam.height == 60.0, "beam height should be 60 cm (cm)"
        assert beam.concrete == Concrete.C25, "beam concrete should be C25"
        assert beam.steel == Steel.CA50, "beam steel should be CA50"


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
        """A point on an interior support becomes one point 0.01 cm to each side (cm, kN.m)."""
        analysis = types.SimpleNamespace(
            moment_extremes_per_segment=lambda: [(300.0, -60.0)],
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
        assert points[0][1] == points[1][1] == -60.0, (
            "both split points keep the support's moment (kN.m)"
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
        return types.SimpleNamespace(width=20.0, height=60.0, concrete=Concrete.C25)

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
        )

        def analyse_beam(*args: object) -> types.SimpleNamespace:
            return analysis

        def build_rebar_calculator(
            self: BeamCalculator,
            structural_beam: object,
            moment: float,
            position: float,
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

        monkeypatch.setattr(beam_calculator, "analyse_beam", analyse_beam)
        monkeypatch.setattr(
            BeamCalculator, "_build_rebar_calculator", build_rebar_calculator
        )
        monkeypatch.setattr(BeamCalculator, "_store_reinforcement", store_reinforcement)
        monkeypatch.setattr(BeamCalculator, "_verify_deformation", verify_deformation)
        monkeypatch.setattr(beam_calculator, "coordinate_span", coordinate_span)
        spans = [_make_span_stub(length_cm=300.0), _make_span_stub(length_cm=200.0)]
        bc = BeamCalculator(_make_beam_stub(spans=spans), _make_registry())  # type: ignore[arg-type]

        bc.run()

        assert len(coordinated) == 2, "each span should be coordinated once"
        for actual, expected in zip(coordinated[0], [150.0, 299.99], strict=True):
            assert_approx(
                actual, expected, "first span: midspan point and support's left (cm)"
            )
        for actual, expected in zip(coordinated[1], [300.01, 420.0], strict=True):
            assert_approx(
                actual, expected, "second span: support's right and midspan point (cm)"
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
            shear_force=lambda position: 50.0,  # pyright: ignore[reportUnknownLambdaType]
        )

        def analyse_beam(*args: object) -> types.SimpleNamespace:
            return analysis

        built: list[tuple[float, float]] = []

        def build_rebar_calculator(
            self: BeamCalculator,
            structural_beam: object,
            moment: float,
            position: float,
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
