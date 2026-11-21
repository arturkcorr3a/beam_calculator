"""Tests for ``src/analysis/anastruct_analysis.py``.

anaStruct is an Euler–Bernoulli solver, so every reference value is the
closed-form result of classical beam theory for a C25/CA50 20x60 cm section
(no shear-deformation term).

anaStruct restrains rotations at fixed supports and springs only to about
1e-7 relative precision, so statically indeterminate results use
``abs_tol=1e-4``.
"""

import math

import pytest

from src.analysis.anastruct_analysis import AnaStructBeamAnalysis
from src.analysis.beam_analysis import BeamAnalysis
from src.analysis.model import BeamSupport, DistributedLoad
from src.analysis.solver import analyse_beam
from src.config import APP_CONFIG
from src.errors import EnginePreconditionError
from src.properties.concrete import Concrete
from src.properties.steel import Steel
from src.structural_elements.rectangular_beam import RectangularBeam
from tests.helpers import assert_approx

_Q = 10.0  # kN/m, downward

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture(autouse=True)
def pinned_concrete(monkeypatch: pytest.MonkeyPatch) -> None:
    """Pin the project concrete to C25 for every test in this module"""
    monkeypatch.setattr(APP_CONFIG, "pavement_concrete", Concrete.C25)


def _section(length: float, label: str = "") -> RectangularBeam:
    """Return a CA50 20x60 cm section of the given length (cm)."""
    return RectangularBeam(
        length=length,
        width=20.0,
        height=60.0,
        steel=Steel.CA50,
        label=label,
    )


def _solve(
    supports: list[BeamSupport],
    length: float = 600.0,
    loads: list[DistributedLoad] | None = None,
) -> AnaStructBeamAnalysis:
    """Solve the section under a full-length downward UDL of 10 kN/m by default."""
    if loads is None:
        loads = [DistributedLoad(0.0, length, _Q)]
    return AnaStructBeamAnalysis(_section(length), supports, loads)


def _bending_stiffness() -> float:
    """Return EI of the 20x60 C25 section (kN.m²)."""
    inertia = 20.0 * 60.0**3 / 12  # cm⁴
    return Concrete.C25.ecs * inertia * 1e-5  # MPa·cm⁴ → kN·m²


@pytest.fixture
def two_span_beam() -> AnaStructBeamAnalysis:
    """Two equal 3 m spans, pinned at 0, 300 and 600 cm, 10 kN/m."""
    return _solve([BeamSupport(0.0), BeamSupport(300.0), BeamSupport(600.0)])


@pytest.fixture
def fixed_fixed_beam() -> AnaStructBeamAnalysis:
    """Single 6 m span, fixed at both ends, 10 kN/m."""
    return _solve([BeamSupport(0.0, math.inf), BeamSupport(600.0, math.inf)])


@pytest.fixture
def propped_cantilever_beam() -> AnaStructBeamAnalysis:
    """Single 6 m span, fixed at x = 0 and pinned at x = 600 cm, 10 kN/m."""
    return _solve([BeamSupport(0.0, math.inf), BeamSupport(600.0)])


@pytest.fixture
def simply_supported_beam() -> AnaStructBeamAnalysis:
    """Single 5 m span, pinned at both ends, 10 kN/m."""
    return _solve([BeamSupport(0.0), BeamSupport(500.0)], length=500.0)


# ---------------------------------------------------------------------------
# TestMomentZeros
# ---------------------------------------------------------------------------


class TestMomentZeros:
    """Tests for ``moment_zeros``."""

    def test_two_span_zeros(self, two_span_beam: AnaStructBeamAnalysis) -> None:
        """Two equal spans: M = 0 at both ends and at 3L/4 from each end support (cm)."""
        zeros = two_span_beam.moment_zeros()
        assert len(zeros) == 4, "Expected zeros at 0, 225, 375 and 600 cm"
        assert_approx(zeros[0], 0.0, "Left pinned end (cm)", abs_tol=1e-6)
        assert_approx(zeros[1], 225.0, "Left inflection point, 3L/4 (cm)", abs_tol=0.01)
        assert_approx(zeros[2], 375.0, "Right inflection point (cm)", abs_tol=0.01)
        assert_approx(zeros[3], 600.0, "Right pinned end (cm)", abs_tol=1e-6)

    def test_fixed_fixed_zeros(self, fixed_fixed_beam: AnaStructBeamAnalysis) -> None:
        """Fixed-fixed: M = 0 at L(1/2 ∓ 1/(2√3)), not at the fixed ends (cm)."""
        zeros = fixed_fixed_beam.moment_zeros()
        offset = 600.0 / (2 * math.sqrt(3))
        assert len(zeros) == 2, "Fixed ends carry moment; only two inflection points"
        assert_approx(
            zeros[0], 300.0 - offset, "Left inflection point (cm)", abs_tol=0.01
        )
        assert_approx(
            zeros[1], 300.0 + offset, "Right inflection point (cm)", abs_tol=0.01
        )

    def test_propped_cantilever_zeros(
        self, propped_cantilever_beam: AnaStructBeamAnalysis
    ) -> None:
        """Propped cantilever: M = 0 at L/4 from the fixed end and at the pinned end (cm)."""
        zeros = propped_cantilever_beam.moment_zeros()
        assert len(zeros) == 2, "Expected the inflection point and the pinned end"
        assert_approx(zeros[0], 150.0, "Inflection point at L/4 (cm)", abs_tol=0.01)
        assert_approx(zeros[1], 600.0, "Pinned right end (cm)", abs_tol=1e-6)


# ---------------------------------------------------------------------------
# TestMomentExtremesPerSegment
# ---------------------------------------------------------------------------


class TestMomentExtremesPerSegment:
    """Tests for ``moment_extremes_per_segment``."""

    def test_two_span_extremes(self, two_span_beam: AnaStructBeamAnalysis) -> None:
        """Two spans: sagging 9qL²/128 at 3L/8, hogging -qL²/8 at the central support."""
        extremes = two_span_beam.moment_extremes_per_segment()
        assert len(extremes) == 3, "Four boundary points create three segments"
        expected = [(112.5, 6.328125), (300.0, -11.25), (487.5, 6.328125)]
        for (position, moment), (exp_position, exp_moment) in zip(
            extremes, expected, strict=True
        ):
            assert_approx(position, exp_position, "Extreme position (cm)", abs_tol=0.01)
            assert_approx(moment, exp_moment, "Extreme moment (kN.m)", abs_tol=0.01)

    def test_fixed_fixed_extremes(
        self, fixed_fixed_beam: AnaStructBeamAnalysis
    ) -> None:
        """Fixed-fixed: -qL²/12 at the ends, +qL²/24 at mid-span (kN.m)."""
        extremes = fixed_fixed_beam.moment_extremes_per_segment()
        assert len(extremes) == 3, "End segments are padded with the domain bounds"
        assert_approx(extremes[0][0], 0.0, "Left extreme at the fixed end (cm)")
        assert_approx(extremes[0][1], -30.0, "Fixed-end moment (kN.m)", abs_tol=0.01)
        assert_approx(extremes[1][0], 300.0, "Mid-span extreme (cm)", abs_tol=0.01)
        assert_approx(extremes[1][1], 15.0, "Mid-span moment (kN.m)", abs_tol=0.01)

    def test_propped_cantilever_fixed_end_extreme(
        self, propped_cantilever_beam: AnaStructBeamAnalysis
    ) -> None:
        """Propped cantilever: the first segment's extreme is -qL²/8 at the fixed end."""
        position, moment = propped_cantilever_beam.moment_extremes_per_segment()[0]
        assert_approx(position, 0.0, "Extreme at the fixed end (cm)")
        assert_approx(moment, -45.0, "Fixed-end moment -qL²/8 (kN.m)", abs_tol=0.01)


# ---------------------------------------------------------------------------
# TestMomentExtremeInRange
# ---------------------------------------------------------------------------


class TestMomentExtremeInRange:
    """Tests for ``moment_extreme_in_range``."""

    def test_range_with_vertex_returns_vertex(
        self, two_span_beam: AnaStructBeamAnalysis
    ) -> None:
        """[0, 200] cm holds the first span's vertex: 9qL²/128 at 3L/8."""
        position, moment = two_span_beam.moment_extreme_in_range(0.0, 200.0)
        assert_approx(position, 112.5, "Vertex position (cm)", abs_tol=0.01)
        assert_approx(moment, 6.328125, "Vertex moment (kN.m)", abs_tol=0.01)

    def test_range_without_vertex_returns_greatest_end(
        self, two_span_beam: AnaStructBeamAnalysis
    ) -> None:
        """[0, 100] cm stops before the vertex, so the dominant moment is at 100 cm."""
        position, moment = two_span_beam.moment_extreme_in_range(0.0, 100.0)
        assert_approx(position, 100.0, "Range end position (cm)")
        assert_approx(moment, 6.25, "M = 11.25·1 - 5·1² (kN.m)", abs_tol=0.01)

    def test_hogging_range_keeps_negative_sign(
        self, two_span_beam: AnaStructBeamAnalysis
    ) -> None:
        """[250, 350] cm around the central support returns -qL²/8 at the support."""
        position, moment = two_span_beam.moment_extreme_in_range(250.0, 350.0)
        assert_approx(position, 300.0, "Central support position (cm)", abs_tol=0.01)
        assert_approx(moment, -11.25, "Support moment (kN.m)", abs_tol=0.01)


# ---------------------------------------------------------------------------
# TestPositionsForMoment
# ---------------------------------------------------------------------------


class TestPositionsForMoment:
    """Tests for ``positions_for_moment``."""

    def test_reachable_target(self, two_span_beam: AnaStructBeamAnalysis) -> None:
        """M = 5 kN.m solves 5x² - 11.25x + 5 = 0 in each span (x in m)."""
        positions = two_span_beam.positions_for_moment(5.0)
        root = math.sqrt(11.25**2 - 100)  # discriminant of 5x² - 11.25x + 5
        first = (11.25 - root) / 10 * 100  # cm
        second = (11.25 + root) / 10 * 100  # cm
        expected = [first, second, 600.0 - second, 600.0 - first]
        assert len(positions) == 4, "M = 5 kN.m is reached twice in each span"
        for actual, exp in zip(positions, expected, strict=True):
            assert_approx(actual, exp, "Crossing of M = 5 kN.m (cm)", abs_tol=0.01)

    def test_unreachable_target(self, two_span_beam: AnaStructBeamAnalysis) -> None:
        """A target above the maximum |M| returns an empty list."""
        assert two_span_beam.positions_for_moment(99.0) == [], (
            "An unreachable target moment should return []"
        )

    def test_hogging_target_is_symmetric(
        self, fixed_fixed_beam: AnaStructBeamAnalysis
    ) -> None:
        """M = -25 kN.m is reached at x = 3 ∓ √8 m, symmetric about mid-span (cm)."""
        positions = fixed_fixed_beam.positions_for_moment(-25.0)
        assert len(positions) == 2, "M = -25 kN.m is reached near each fixed end"
        assert_approx(
            positions[0], (3 - math.sqrt(8)) * 100, "Left crossing (cm)", abs_tol=0.01
        )
        assert_approx(
            positions[0] + positions[1], 600.0, "Symmetric positions sum to L (cm)"
        )


# ---------------------------------------------------------------------------
# TestPositionsForShear
# ---------------------------------------------------------------------------


class TestPositionsForShear:
    """Tests for ``positions_for_shear``."""

    def test_reachable_targets(
        self, simply_supported_beam: AnaStructBeamAnalysis
    ) -> None:
        """V = ±10 kN solves 25 - 10x = ±10 at x = 1.5 m and 3.5 m (cm)."""
        positive = simply_supported_beam.positions_for_shear(10.0)
        negative = simply_supported_beam.positions_for_shear(-10.0)
        assert len(positive) == 1, "Linear shear reaches V = +10 kN once"
        assert len(negative) == 1, "Linear shear reaches V = -10 kN once"
        assert_approx(positive[0], 150.0, "Crossing of V = +10 kN (cm)", abs_tol=0.01)
        assert_approx(negative[0], 350.0, "Crossing of V = -10 kN (cm)", abs_tol=0.01)

    def test_unreachable_target(
        self, simply_supported_beam: AnaStructBeamAnalysis
    ) -> None:
        """A target above the maximum |V| returns an empty list."""
        assert simply_supported_beam.positions_for_shear(30.0) == [], (
            "An unreachable target shear should return []"
        )

    def test_one_crossing_per_span(self, two_span_beam: AnaStructBeamAnalysis) -> None:
        """Two spans: V = 0 at 3L/8 from each end support (cm)."""
        positions = two_span_beam.positions_for_shear(0.0)
        assert len(positions) == 2, "V = 0 is reached once in each span"
        assert_approx(positions[0], 112.5, "Left span crossing (cm)", abs_tol=0.01)
        assert_approx(positions[1], 487.5, "Right span crossing (cm)", abs_tol=0.01)

    def test_jump_over_support_is_not_reached(
        self, two_span_beam: AnaStructBeamAnalysis
    ) -> None:
        """V jumps from -18.75 to +18.75 kN over the central support; V = 15 kN only lies on the right span's line, 18.75 - 10x = 15 (cm)."""
        positions = two_span_beam.positions_for_shear(15.0)
        assert len(positions) == 1, (
            "The jump over the central support should not count as a crossing"
        )
        assert_approx(positions[0], 337.5, "Right span crossing (cm)", abs_tol=0.01)

    def test_crossing_on_element_boundary_is_not_duplicated(self) -> None:
        """A load split at mid-span puts V = 0 on the shared element end (cm)."""
        analysis = _solve(
            [BeamSupport(0.0), BeamSupport(500.0)],
            length=500.0,
            loads=[DistributedLoad(0.0, 250.0, _Q), DistributedLoad(250.0, 500.0, _Q)],
        )
        positions = analysis.positions_for_shear(0.0)
        assert len(positions) == 1, "Both elements report the shared end only once"
        assert_approx(positions[0], 250.0, "Mid-span crossing (cm)", abs_tol=0.01)


# ---------------------------------------------------------------------------
# TestPointQueries
# ---------------------------------------------------------------------------


class TestPointQueries:
    """Tests for point queries on a simply supported 5 m span, 10 kN/m."""

    def test_length(self, simply_supported_beam: AnaStructBeamAnalysis) -> None:
        """Length is the section length (cm)."""
        assert_approx(simply_supported_beam.length, 500.0, "Beam length (cm)")

    def test_mid_span_moment(
        self, simply_supported_beam: AnaStructBeamAnalysis
    ) -> None:
        """A downward load gives M_mid = +qL²/8 (kN.m)."""
        assert_approx(
            simply_supported_beam.bending_moment(250.0),
            31.25,
            "Mid-span moment qL²/8 (kN.m)",
            abs_tol=1e-6,
        )

    def test_shear_force(self, simply_supported_beam: AnaStructBeamAnalysis) -> None:
        """Shear is +qL/2 at the left support and zero at mid-span (kN)."""
        assert_approx(
            simply_supported_beam.shear_force(0.0),
            25.0,
            "Left-end shear (kN)",
            abs_tol=1e-6,
        )
        assert_approx(
            simply_supported_beam.shear_force(250.0),
            0.0,
            "Mid-span shear (kN)",
            abs_tol=1e-6,
        )

    def test_reaction(self, simply_supported_beam: AnaStructBeamAnalysis) -> None:
        """Each support reacts with qL/2 upward (kN)."""
        assert_approx(
            simply_supported_beam.reaction(0.0),
            25.0,
            "Left reaction (kN)",
            abs_tol=1e-6,
        )

    def test_reaction_without_support_raises(
        self, simply_supported_beam: AnaStructBeamAnalysis
    ) -> None:
        """Asking for a reaction where there is no support raises ValueError."""
        with pytest.raises(EnginePreconditionError, match="No support"):
            simply_supported_beam.reaction(250.0)

    def test_max_abs_shear(self, simply_supported_beam: AnaStructBeamAnalysis) -> None:
        """Maximum absolute shear equals the reaction, qL/2 (kN)."""
        assert_approx(
            simply_supported_beam.max_abs_shear(), 25.0, "Max |V| (kN)", abs_tol=1e-6
        )

    def test_mid_span_deflection(
        self, simply_supported_beam: AnaStructBeamAnalysis
    ) -> None:
        """Mid-span deflection is -5qL⁴/(384EI), downward negative (cm)."""
        expected = -5 * _Q * 5.0**4 / (384 * _bending_stiffness()) * 100  # m → cm
        assert_approx(
            simply_supported_beam.deflection(250.0),
            expected,
            "Mid-span deflection 5qL⁴/(384EI) (cm)",
            abs_tol=1e-6,
        )

    def test_max_abs_shear_picks_negative_extreme(self) -> None:
        """Pinned-left, fixed-right 6 m span: |V| peaks at the fixed end, 5qL/8 (kN)."""
        analysis = _solve([BeamSupport(0.0), BeamSupport(600.0, math.inf)])
        assert_approx(
            analysis.max_abs_shear(), 37.5, "Max |V| = 5qL/8 (kN)", abs_tol=1e-4
        )


# ---------------------------------------------------------------------------
# TestRotationalSprings
# ---------------------------------------------------------------------------


class TestRotationalSprings:
    """Tests for elastic-fixed supports (rotational springs)."""

    def test_spring_end_moment_matches_closed_form(self) -> None:
        """Symmetric span with k = 2EI/L: M_end = (qL²/12)/(1 + 2EI/(kL)) = qL²/24 (kN.m)."""
        stiffness = 2 * _bending_stiffness() / 5.0  # kN.m/rad
        analysis = _solve(
            [BeamSupport(0.0, stiffness), BeamSupport(500.0, stiffness)], length=500.0
        )
        end_moment = -(_Q * 5.0**2 / 12) / 2  # hogging
        assert_approx(
            analysis.bending_moment(0.0),
            end_moment,
            "Spring end moment (kN.m)",
            abs_tol=1e-4,
        )
        assert_approx(
            analysis.bending_moment(250.0),
            _Q * 5.0**2 / 8 + end_moment,
            "Mid-span moment = qL²/8 + M_end (kN.m)",
            abs_tol=1e-4,
        )

    def test_very_stiff_spring_approaches_fixed_end(self) -> None:
        """A very large k reproduces the fixed-end moment -qL²/12 (kN.m)."""
        analysis = _solve(
            [BeamSupport(0.0, 1e12), BeamSupport(500.0, 1e12)], length=500.0
        )
        assert_approx(
            analysis.bending_moment(0.0),
            -(_Q * 5.0**2 / 12),
            "Stiff spring should behave as fixed (kN.m)",
            abs_tol=1e-3,
        )

    @pytest.fixture
    def spring_two_span_beam(self) -> AnaStructBeamAnalysis:
        """Two 3 m spans, pinned ends, a rotational spring on the central support, load on the right span only (so the support rotates)."""
        stiffness = _bending_stiffness() / 3.0  # kN.m/rad
        return _solve(
            [BeamSupport(0.0), BeamSupport(300.0, stiffness), BeamSupport(600.0)],
            loads=[DistributedLoad(300.0, 600.0, _Q)],
        )

    def test_moment_jumps_over_spring_support(
        self, spring_two_span_beam: AnaStructBeamAnalysis
    ) -> None:
        """The spring support applies a concentrated moment, so the moment on its two sides differs (kN.m)."""
        left = spring_two_span_beam.bending_moment(300.0)
        right = spring_two_span_beam.bending_moment(300.0, from_right=True)
        assert abs(left - right) > 1e-3, "the moment should jump over the support"

    def test_no_jump_without_support_rotation(self) -> None:
        """A symmetric beam on a stiff spring has no rotation at the support, so no jump; nor does a pinned end (kN.m)."""
        beam = _solve([BeamSupport(0.0), BeamSupport(300.0, 1e12), BeamSupport(600.0)])
        assert_approx(
            beam.bending_moment(300.0, from_right=True),
            beam.bending_moment(300.0),
            "Stiff spring on a symmetric beam: both sides equal (kN.m)",
            abs_tol=1e-3,
        )
        assert_approx(
            beam.bending_moment(0.0, from_right=True),
            beam.bending_moment(0.0),
            "No jump at a pinned end (kN.m)",
            abs_tol=1e-6,
        )

    def test_extreme_in_range_sees_right_side_of_jump(self) -> None:
        """When |M| is larger just right of the spring support, the range extreme is that value (kN.m)."""
        stiffness = _bending_stiffness() / 3.0
        beam = _solve(
            [BeamSupport(0.0), BeamSupport(300.0, stiffness), BeamSupport(600.0)],
            loads=[DistributedLoad(300.0, 600.0, _Q)],
        )
        left = beam.bending_moment(300.0)
        right = beam.bending_moment(300.0, from_right=True)
        assert abs(right) > abs(left), "setup: the right side should dominate"
        position, moment = beam.moment_extreme_in_range(299.0, 301.0)
        assert_approx(position, 300.0, "Support position (cm)", abs_tol=0.01)
        assert_approx(moment, right, "Right-side moment (kN.m)", abs_tol=1e-6)

    def test_negative_stiffness_raises(self) -> None:
        """A negative rotational stiffness raises ValueError."""
        supports = [BeamSupport(0.0, -1.0), BeamSupport(600.0)]
        with pytest.raises(EnginePreconditionError, match="non-negative"):
            _solve(supports)


# ---------------------------------------------------------------------------
# TestModelBuilding
# ---------------------------------------------------------------------------


class TestModelBuilding:
    """Tests for element splitting and input validation."""

    def test_partial_load_across_support_is_in_equilibrium(self) -> None:
        """A load from 100 to 450 cm over a two-span beam: Σ reactions = q·3.5 m (kN)."""
        analysis = _solve(
            [BeamSupport(0.0), BeamSupport(300.0), BeamSupport(600.0)],
            loads=[DistributedLoad(100.0, 450.0, _Q)],
        )
        total = sum(analysis.reaction(x) for x in (0.0, 300.0, 600.0))
        assert_approx(
            total, _Q * 3.5, "Reactions balance the applied load (kN)", abs_tol=1e-6
        )

    def test_unloaded_stretch_has_linear_moment(self) -> None:
        """Between the support and the load start, M varies linearly (kN.m)."""
        analysis = _solve(
            [BeamSupport(0.0), BeamSupport(600.0)],
            loads=[DistributedLoad(300.0, 600.0, _Q)],
        )
        midpoint = analysis.bending_moment(150.0)
        assert_approx(
            midpoint,
            analysis.bending_moment(300.0) / 2,
            "Unloaded stretch from a pinned end is linear (kN.m)",
            abs_tol=1e-6,
        )

    def test_support_outside_beam_raises(self) -> None:
        """A support beyond the beam length raises ValueError."""
        supports = [BeamSupport(0.0), BeamSupport(700.0)]
        with pytest.raises(EnginePreconditionError, match="outside the beam"):
            _solve(supports)


# ---------------------------------------------------------------------------
# TestFactory
# ---------------------------------------------------------------------------


class TestFactory:
    """Tests for ``analyse_beam``."""

    def test_analyse_beam_uses_anastruct(self) -> None:
        """analyse_beam returns an AnaStructBeamAnalysis."""
        analysis: BeamAnalysis = analyse_beam(
            _section(500.0),
            [BeamSupport(0.0), BeamSupport(500.0)],
            [DistributedLoad(0.0, 500.0, _Q)],
        )
        assert isinstance(analysis, AnaStructBeamAnalysis), (
            "analyse_beam should use the anaStruct solver"
        )
