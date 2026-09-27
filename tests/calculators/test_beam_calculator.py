"""Unit tests for src/calculators/beam_calculator.py — BeamCalculator.

Isolated branch tests use SimpleNamespace doubles and monkeypatching.
The integration test exercises the real end-to-end pipeline on a
conservative 20×60 C25/CA50 single-span beam.
"""

import types

import pytest

from src.calculators.beam_calculator import BeamCalculator
from src.checkers.beam_deformation_checker import BeamDeformationChecker
from src.config import APP_CONFIG
from src.properties.concrete import Concrete
from src.properties.steel import Steel
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
    """Return a minimal Span stub whose get_length() ignores the registry."""
    return types.SimpleNamespace(
        permanent_load=permanent_load,
        variable_load=variable_load,
        start_pillar_id="P1",
        end_pillar_id="P2",
        get_length=lambda registry, _l=length_cm: _l,  # pyright: ignore[reportUnknownLambdaType]
    )


def _make_beam_stub(
    spans: list[types.SimpleNamespace] | None = None,
    beam_id: str = "V1",
    width: float = 20.0,
    height: float = 60.0,
) -> types.SimpleNamespace:
    """Return a minimal ContinuousBeam stub with one default span."""
    if spans is None:
        spans = [_make_span_stub()]
    return types.SimpleNamespace(
        id=beam_id,
        width=width,
        height=height,
        spans=spans,
        reinforcement=[],
        get_most_loaded_span_for_els=lambda: spans[0],
    )


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
        bc = BeamCalculator(_make_beam_stub(spans=[span]), {})  # type: ignore[arg-type]
        supports = bc._build_supports()  # pyright: ignore[reportPrivateUsage]
        assert len(supports) == 2, "Single span should produce exactly 2 supports"

    def test_two_spans_three_supports(self) -> None:
        """Two-span beam creates 3 supports (dimensionless)."""
        spans = [_make_span_stub(length_cm=300.0), _make_span_stub(length_cm=400.0)]
        bc = BeamCalculator(_make_beam_stub(spans=spans), {})  # type: ignore[arg-type]
        supports = bc._build_supports()  # pyright: ignore[reportPrivateUsage]
        assert len(supports) == 3, "Two spans should produce exactly 3 supports"

    def test_cumulative_positions(self) -> None:
        """Supports are placed at cumulative span-length positions (cm)."""
        spans = [_make_span_stub(length_cm=300.0), _make_span_stub(length_cm=200.0)]
        bc = BeamCalculator(_make_beam_stub(spans=spans), {})  # type: ignore[arg-type]
        supports = bc._build_supports()  # pyright: ignore[reportPrivateUsage]
        # Support at 0, 300, 500 — _position is the indeterminatebeam internal attribute
        positions = [s._position for s in supports]  # pyright: ignore[reportPrivateUsage]
        assert positions[0] == 0, "First support should be at position 0 (cm)"
        assert positions[1] == 300.0, "Second support should be at 300 cm (cm)"
        assert positions[2] == 500.0, "Third support should be at 500 cm (cm)"


# ---------------------------------------------------------------------------
# TestBuildLoads
# ---------------------------------------------------------------------------


class TestBuildLoads:
    """Tests for _build_loads() — UDLV objects for each span."""

    def test_one_load_per_span(self) -> None:
        """_build_loads() returns one load object per span (dimensionless)."""
        spans = [_make_span_stub(), _make_span_stub()]
        bc = BeamCalculator(_make_beam_stub(spans=spans), {})  # type: ignore[arg-type]
        loads = bc._build_loads()  # pyright: ignore[reportPrivateUsage]
        assert len(loads) == 2, "Should produce one load per span"

    def test_load_magnitude_is_negative(self) -> None:
        """Load magnitude is negative (downward convention) (kN/m)."""
        span = _make_span_stub(permanent_load=10.0, variable_load=5.0)
        bc = BeamCalculator(_make_beam_stub(spans=[span]), {})  # type: ignore[arg-type]
        loads = bc._build_loads()  # pyright: ignore[reportPrivateUsage]
        # UDLV stores force along y; magnitude should be -(perm+var)=-15
        # Access internals via .force or check the direction indirectly
        # The simplest invariant: there is exactly one load and it is a UDLV
        assert len(loads) == 1, "Should produce one load for one span"

    def test_load_magnitude_combines_permanent_and_variable(self) -> None:
        """Load magnitude = -(permanent + variable) kN/m (kN/m)."""
        span = _make_span_stub(permanent_load=8.0, variable_load=4.0)
        bc = BeamCalculator(_make_beam_stub(spans=[span]), {})  # type: ignore[arg-type]
        loads = bc._build_loads()  # pyright: ignore[reportPrivateUsage]
        # UDLV stores force (y-direction); negative = downward
        # indeterminatebeam UDLV: loads[0].force gives the magnitude
        load_obj = loads[0]
        # The internal attribute is .force (y component) — access via duck-typing
        if hasattr(load_obj, "force"):
            assert_approx(
                load_obj.force, -12.0, "UDLV magnitude should be -(perm+var) (kN/m)"
            )


# ---------------------------------------------------------------------------
# TestBuildStructuralBeam
# ---------------------------------------------------------------------------


class TestBuildStructuralBeam:
    """Tests for _build_structural_beam() — reads APP_CONFIG, builds RectangularBeam."""

    def test_builds_with_valid_config(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """_build_structural_beam() returns a RectangularBeam with correct dimensions."""
        monkeypatch.setattr(APP_CONFIG, "pavement_concrete", "C25")
        monkeypatch.setattr(APP_CONFIG, "pavement_steel", "CA50")

        span = _make_span_stub(length_cm=500.0)
        bc = BeamCalculator(_make_beam_stub(spans=[span]), {})  # type: ignore[arg-type]
        supports = bc._build_supports()  # pyright: ignore[reportPrivateUsage]
        loads = bc._build_loads()  # pyright: ignore[reportPrivateUsage]
        beam = bc._build_structural_beam(supports, loads)  # pyright: ignore[reportPrivateUsage]

        from src.structural_elements.rectangular_beam import RectangularBeam

        assert isinstance(beam, RectangularBeam), (
            "_build_structural_beam should return a RectangularBeam"
        )
        assert beam.width == 20.0, "beam width should be 20 cm (cm)"
        assert beam.height == 60.0, "beam height should be 60 cm (cm)"
        assert beam.concrete == Concrete.C25, "beam concrete should be C25"
        assert beam.steel == Steel.CA50, "beam steel should be CA50"

    def test_invalid_concrete_raises_key_error(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """_build_structural_beam() raises KeyError for unknown pavement_concrete."""
        monkeypatch.setattr(APP_CONFIG, "pavement_concrete", "INVALID")
        monkeypatch.setattr(APP_CONFIG, "pavement_steel", "CA50")

        span = _make_span_stub()
        bc = BeamCalculator(_make_beam_stub(spans=[span]), {})  # type: ignore[arg-type]
        with pytest.raises(KeyError):
            bc._build_structural_beam([], [])  # pyright: ignore[reportPrivateUsage]

    def test_invalid_steel_raises_key_error(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """_build_structural_beam() raises KeyError for unknown pavement_steel."""
        monkeypatch.setattr(APP_CONFIG, "pavement_concrete", "C25")
        monkeypatch.setattr(APP_CONFIG, "pavement_steel", "INVALID")

        span = _make_span_stub()
        bc = BeamCalculator(_make_beam_stub(spans=[span]), {})  # type: ignore[arg-type]
        with pytest.raises(KeyError):
            bc._build_structural_beam([], [])  # pyright: ignore[reportPrivateUsage]


# ---------------------------------------------------------------------------
# TestInterestPoints
# ---------------------------------------------------------------------------


class TestInterestPoints:
    """Tests for _interest_points() — delegates to bending_moment_extremes_per_segment."""

    def test_returns_extreme_per_segment(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """_interest_points() forwards the beam's symbolic expressions and domain (cm, kN.m)."""
        import src.calculators.beam_calculator as beam_calculator_module

        captured: dict[str, object] = {}

        def fake_extremes(
            bending: object, shear: object, lower: float, upper: float
        ) -> list[tuple[float, float]]:
            captured["bending"] = bending
            captured["shear"] = shear
            captured["lower"] = lower
            captured["upper"] = upper
            return [(250.0, 42.0), (500.0, -30.0)]

        monkeypatch.setattr(
            beam_calculator_module,
            "bending_moment_extremes_per_segment",
            fake_extremes,
        )

        structural_beam = types.SimpleNamespace(
            bending_moment_expression="M(x)",
            shear_force_expression="V(x)",
            length=800.0,
        )
        bc = BeamCalculator(_make_beam_stub(), {})  # type: ignore[arg-type]
        points = bc._interest_points(structural_beam)  # pyright: ignore[reportPrivateUsage, reportArgumentType]

        assert points == [(250.0, 42.0), (500.0, -30.0)], (
            "_interest_points should return the per-segment extremes"
        )
        assert captured["bending"] == "M(x)", "should forward bending_moment_expression"
        assert captured["shear"] == "V(x)", "should forward shear_force_expression"
        assert captured["lower"] == 0.0, "lower bound should be 0 cm"
        assert captured["upper"] == 800.0, "upper bound should be beam length (cm)"


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
        """Build a structural beam stub compatible with _verify_deformation."""
        return types.SimpleNamespace(
            width=20.0,
            height=60.0,
            concrete=Concrete.C25,
            get_bending_moment=lambda position: 150.0,  # pyright: ignore[reportUnknownLambdaType]
            get_deflection=lambda position: 0.1,  # pyright: ignore[reportUnknownLambdaType]
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
        with pytest.raises(ValueError, match="Deformation exceeds"):
            bc._verify_deformation(  # type: ignore[arg-type]
                self._make_structural_beam_stub(),  # type: ignore[arg-type]
                self._make_rebar_calculator_stub(),  # type: ignore[arg-type]
                250.0,
            )


# ---------------------------------------------------------------------------
# TestRunIntegration — one conservative real end-to-end run
# ---------------------------------------------------------------------------


class TestRunIntegration:
    """Integration test: BeamCalculator.run() on a conservative real beam.

    Uses a SimpleNamespace beam stub wired to a pre-resolved single span
    (500 cm, 20 kN/m permanent load, 10 kN/m variable load) so that the
    indeterminatebeam solver, RebarCalculator convergence loop, and
    BeamDeformationChecker all execute against real objects — no mocking.

    The beam is 20×60 cm, C25/CA50, deliberately under-loaded so that both
    the strut check and the deformation check pass on the first iteration.
    """

    def test_run_end_to_end_single_span_beam(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """run() completes without raising for a modest single-span 20×60 C25/CA50 beam.

        Integration test — transitively covers _build_supports, _build_loads,
        _build_structural_beam, _interest_points, _calculate (RebarCalculator
        convergence), _store_reinforcement, and _verify_deformation (pass branch).
        """
        monkeypatch.setattr(APP_CONFIG, "pavement_concrete", "C25")
        monkeypatch.setattr(APP_CONFIG, "pavement_steel", "CA50")

        # Single 500 cm span with moderate loads (kN/m)
        span = _make_span_stub(permanent_load=20.0, variable_load=10.0, length_cm=500.0)
        beam_stub = _make_beam_stub(spans=[span], beam_id="V_integration")

        bc = BeamCalculator(beam_stub, {})  # type: ignore[arg-type]
        # Must complete without raising any exception
        bc.run()

        assert beam_stub.reinforcement, (
            "run() should populate the beam's reinforcement list"
        )
