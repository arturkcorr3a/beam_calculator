"""Tests for the bending-moment analysis functions in ``src/loading/forces.py``.

All three fixtures build real ``RectangularBeam`` instances with C25/CA50
material properties so that the reference values account for the actual
stiffness distribution rather than the idealized unit-beam values used in
the design notes.

Reference values were verified by running the functions against the fixtures
and cross-checking against ``get_max_bending_moment`` and manual equilibrium
checks.
"""

import pytest
from indeterminatebeam import Support  # type: ignore
from indeterminatebeam.loading import UDLV  # type: ignore
from sympy.sets.sets import FiniteSet  # type: ignore
from sympy.sets.sets import Interval as SympyInterval

from src.loading.forces import (
    _extract_finite_zeros,  # pyright: ignore[reportPrivateUsage]
    bending_moment_extremes_per_segment,
    bending_moment_zeros,
    positions_for_bending_moment,
)
from src.properties.concrete import Concrete
from src.properties.steel import Steel
from src.structural_elements.rectangular_beam import RectangularBeam
from tests.helpers import assert_approx

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def simply_supported_two_span_beam() -> RectangularBeam:
    """Build a real C25/CA50 beam with two equal spans.

    Geometry: 600 cm total, pinned supports at x = 0, 300, and 600 cm.
    Load: uniform vertical distributed load of -10 kN/m over the full span.

    The reaction at the central support is larger than at the end supports
    (indeterminate structure), so the zero-crossings are not at the
    symmetric ±75 cm positions of an idealized uniform beam.
    """
    return RectangularBeam(
        length=600.0,
        width=20.0,
        height=60.0,
        concrete=Concrete.C25,
        steel=Steel.CA50,
        supports=[
            Support(0.0, (1, 1, 0)),  # pyright: ignore[reportArgumentType]
            Support(300.0, (1, 1, 0)),  # pyright: ignore[reportArgumentType]
            Support(600.0, (1, 1, 0)),  # pyright: ignore[reportArgumentType]
        ],
        loads=[UDLV(-10.0, (0.0, 600.0))],  # pyright: ignore[reportArgumentType]
        label="two_span",
    )


@pytest.fixture
def fixed_fixed_beam() -> RectangularBeam:
    """Build a real C25/CA50 fixed-fixed beam.

    Geometry: 600 cm, fully fixed at both ends (rotation restrained).
    Load: uniform vertical distributed load of -10 kN/m.

    The fixed-end moments are non-zero, so neither endpoint appears in the
    zeros list from ``bending_moment_zeros``. The segment construction must
    pad with the domain bounds to cover the end regions.
    """
    return RectangularBeam(
        length=600.0,
        width=20.0,
        height=60.0,
        concrete=Concrete.C25,
        steel=Steel.CA50,
        supports=[
            Support(0.0, (1, 1, 1)),  # pyright: ignore[reportArgumentType]
            Support(600.0, (1, 1, 1)),  # pyright: ignore[reportArgumentType]
        ],
        loads=[UDLV(-10.0, (0.0, 600.0))],  # pyright: ignore[reportArgumentType]
        label="fixed_fixed",
    )


@pytest.fixture
def propped_cantilever_beam() -> RectangularBeam:
    """Build a real C25/CA50 propped cantilever beam.

    Geometry: 600 cm, fixed at x = 0 (rotation restrained) and pinned at
    x = 600 cm (free rotation).
    Load: uniform vertical distributed load of -10 kN/m.

    The fixed end carries a non-zero hogging moment. The pinned end has M = 0
    and will appear as a zero. This fixture proves that the unconditional
    domain-bound pad adds the left ``[0.0, zero]`` segment that would otherwise
    be missing from a zeros-only boundary list.
    """
    return RectangularBeam(
        length=600.0,
        width=20.0,
        height=60.0,
        concrete=Concrete.C25,
        steel=Steel.CA50,
        supports=[
            Support(0.0, (1, 1, 1)),  # pyright: ignore[reportArgumentType]
            Support(600.0, (1, 1, 0)),  # pyright: ignore[reportArgumentType]
        ],
        loads=[UDLV(-10.0, (0.0, 600.0))],  # pyright: ignore[reportArgumentType]
        label="propped_cantilever",
    )


# ---------------------------------------------------------------------------
# TestExtractFiniteZeros
# ---------------------------------------------------------------------------


class TestExtractFiniteZeros:
    """Tests for the private ``_extract_finite_zeros`` helper."""

    def test_plain_finite_set_returns_sorted_floats(self) -> None:
        """FiniteSet with multiple values is converted to a sorted float list."""
        finite_set = FiniteSet(3, 1, 2)
        result = _extract_finite_zeros(finite_set, 0.0, 5.0)
        assert result == [1.0, 2.0, 3.0], (
            "Elements of a plain FiniteSet should be returned in sorted order"
        )

    def test_degenerate_interval_is_extracted(self) -> None:
        """A Union containing a degenerate Interval(a, a) contributes the point a."""
        from sympy.sets.sets import Union  # type: ignore

        degenerate = SympyInterval(4.0, 4.0)
        finite_set = FiniteSet(1.0, 2.0)
        union = Union(finite_set, degenerate)
        result = _extract_finite_zeros(union, 0.0, 5.0)
        assert 4.0 in result, "Degenerate Interval(a, a) should contribute point a"
        assert 1.0 in result and 2.0 in result, (
            "FiniteSet elements should also be present"
        )

    def test_proper_interval_is_excluded(self) -> None:
        """A proper Interval(a, b) with a != b is not included."""
        from sympy.sets.sets import Union  # type: ignore

        proper = SympyInterval(1.0, 3.0)
        finite_set = FiniteSet(4.0)
        union = Union(finite_set, proper)
        result = _extract_finite_zeros(union, 0.0, 5.0)
        assert result == [4.0], (
            "A proper Interval(a, b) should be excluded; only the FiniteSet element remains"
        )

    def test_out_of_bounds_values_are_filtered(self) -> None:
        """Values outside [lower_bound, upper_bound] are excluded."""
        finite_set = FiniteSet(0.0, 2.5, 5.0, 7.0)
        result = _extract_finite_zeros(finite_set, 1.0, 6.0)
        assert 0.0 not in result, "Value below lower_bound should be excluded"
        assert 7.0 not in result, "Value above upper_bound should be excluded"
        assert 2.5 in result and 5.0 in result, (
            "Values within bounds should be included"
        )


# ---------------------------------------------------------------------------
# TestBendingMomentZeros
# ---------------------------------------------------------------------------


class TestBendingMomentZeros:
    """Tests for ``bending_moment_zeros``."""

    def test_two_span_includes_endpoint_and_interior_zeros(
        self, simply_supported_two_span_beam: RectangularBeam
    ) -> None:
        """Pinned two-span beam returns the two inflection points plus both endpoints.

        The beam is indeterminate; the central reaction redistributes load, so
        the zeros are not symmetric about the mid-span.
        """
        beam = simply_supported_two_span_beam
        zeros = bending_moment_zeros(
            beam.bending_moment_expression,
            0.0,
            float(beam._x1),  # type: ignore[attr-defined]
        )
        assert len(zeros) == 4, "Expected 4 zeros: x=0, two inflection points, x=600"
        assert_approx(zeros[0], 0.0, "First zero should be at the left pinned end (cm)")
        assert_approx(zeros[1], 226.7578, "Left inflection point (cm)", abs_tol=0.01)
        assert_approx(zeros[2], 373.2422, "Right inflection point (cm)", abs_tol=0.01)
        assert_approx(
            zeros[3], 600.0, "Last zero should be at the right pinned end (cm)"
        )

    def test_propped_cantilever_fixed_end_is_not_a_zero(
        self, propped_cantilever_beam: RectangularBeam
    ) -> None:
        """Fixed end (x = 0) has non-zero moment and must NOT appear in zeros list."""
        beam = propped_cantilever_beam
        zeros = bending_moment_zeros(
            beam.bending_moment_expression,
            0.0,
            float(beam._x1),  # type: ignore[attr-defined]
        )
        assert 0.0 not in zeros, (
            "Fixed end carries a hogging moment; x=0 must not be listed as a zero"
        )

    def test_propped_cantilever_has_one_interior_zero_and_pinned_end(
        self, propped_cantilever_beam: RectangularBeam
    ) -> None:
        """Propped cantilever returns the inflection point and the pinned-end zero."""
        beam = propped_cantilever_beam
        zeros = bending_moment_zeros(
            beam.bending_moment_expression,
            0.0,
            float(beam._x1),  # type: ignore[attr-defined]
        )
        assert len(zeros) == 2, (
            "Expected 2 zeros: one inflection point and the pinned right end"
        )
        assert_approx(
            zeros[0],
            149.1054,
            "Inflection point of propped cantilever (cm)",
            abs_tol=0.01,
        )
        assert_approx(zeros[1], 600.0, "Pinned right end should be a zero (cm)")

    def test_fixed_fixed_has_two_interior_zeros_and_right_endpoint_zero(
        self, fixed_fixed_beam: RectangularBeam
    ) -> None:
        """Fixed-fixed beam zeros include two inflection points and x=600 (M=0 numerically).

        x=0 is NOT a zero (M = -30 kN.m); x=600 IS returned because M(600) = 0.
        """
        beam = fixed_fixed_beam
        zeros = bending_moment_zeros(
            beam.bending_moment_expression,
            0.0,
            float(beam._x1),  # type: ignore[attr-defined]
        )
        assert 0.0 not in zeros, (
            "Fixed left end carries a hogging moment; x=0 must not be a zero"
        )
        assert_approx(
            zeros[0],
            126.7949,
            "Left inflection point of fixed-fixed beam (cm)",
            abs_tol=0.01,
        )
        assert_approx(
            zeros[1],
            473.2051,
            "Right inflection point of fixed-fixed beam (cm)",
            abs_tol=0.01,
        )


# ---------------------------------------------------------------------------
# TestBendingMomentExtremesPerSegment
# ---------------------------------------------------------------------------


class TestBendingMomentExtremesPerSegment:
    """Tests for ``bending_moment_extremes_per_segment``."""

    def test_two_span_returns_three_segments(
        self, simply_supported_two_span_beam: RectangularBeam
    ) -> None:
        """Pinned two-span beam has four boundary points and three segments."""
        beam = simply_supported_two_span_beam
        extremes = bending_moment_extremes_per_segment(
            beam.bending_moment_expression,
            beam.shear_force_expression,
            0.0,
            float(beam._x1),  # type: ignore[attr-defined]
        )
        assert len(extremes) == 3, "Four boundary points create three segments"

    def test_two_span_first_segment_sagging_extreme(
        self, simply_supported_two_span_beam: RectangularBeam
    ) -> None:
        """First span [0, 226.76]: shear zero at 113.38 cm gives positive (sagging) moment."""
        beam = simply_supported_two_span_beam
        extremes = bending_moment_extremes_per_segment(
            beam.bending_moment_expression,
            beam.shear_force_expression,
            0.0,
            float(beam._x1),  # type: ignore[attr-defined]
        )
        x_pos, moment = extremes[0]
        assert_approx(
            x_pos, 113.3789, "Sagging extreme in first span (cm)", abs_tol=0.01
        )
        assert_approx(
            moment, 6.4274, "Sagging moment in first span (kN.m)", abs_tol=0.01
        )

    def test_two_span_middle_segment_hogging_extreme(
        self, simply_supported_two_span_beam: RectangularBeam
    ) -> None:
        """Middle segment [226.76, 373.24]: hogging extreme at the central support (x=300).

        The shear force has a jump discontinuity at x = 300 cm (intermediate
        support reaction). ``solveset`` cannot find this crossing, so the
        Piecewise-breakpoint candidate mechanism must supply x=300 as a candidate.
        """
        beam = simply_supported_two_span_beam
        extremes = bending_moment_extremes_per_segment(
            beam.bending_moment_expression,
            beam.shear_force_expression,
            0.0,
            float(beam._x1),  # type: ignore[attr-defined]
        )
        x_pos, moment = extremes[1]
        assert_approx(
            x_pos, 300.0, "Hogging extreme at central support (cm)", abs_tol=0.01
        )
        assert_approx(
            moment, -10.9863, "Hogging moment at central support (kN.m)", abs_tol=0.01
        )

    def test_two_span_third_segment_sagging_extreme(
        self, simply_supported_two_span_beam: RectangularBeam
    ) -> None:
        """Third segment [373.24, 600]: symmetric sagging extreme matches first span."""
        beam = simply_supported_two_span_beam
        extremes = bending_moment_extremes_per_segment(
            beam.bending_moment_expression,
            beam.shear_force_expression,
            0.0,
            float(beam._x1),  # type: ignore[attr-defined]
        )
        x_pos, moment = extremes[2]
        assert_approx(
            x_pos, 486.6211, "Sagging extreme in third span (cm)", abs_tol=0.01
        )
        assert_approx(
            moment, 6.4274, "Sagging moment in third span (kN.m)", abs_tol=0.01
        )

    def test_fixed_fixed_end_segments_have_fixed_end_moments(
        self, fixed_fixed_beam: RectangularBeam
    ) -> None:
        """Fixed-fixed beam: end segments must be created by the unconditional boundary pad.

        Without the pad, zeros = [126.79, 473.21, 600.0] and boundary_points
        would miss the x=0 end region entirely. With the pad, boundary_points =
        [0.0, 126.79, 473.21, 600.0] and the left-end segment correctly reports
        the fixed-end moment at x=0.
        """
        beam = fixed_fixed_beam
        extremes = bending_moment_extremes_per_segment(
            beam.bending_moment_expression,
            beam.shear_force_expression,
            0.0,
            float(beam._x1),  # type: ignore[attr-defined]
        )
        left_x, left_moment = extremes[0]
        assert_approx(
            left_x, 0.0, "Left-end extreme must be at x=0 (fixed support, cm)"
        )
        assert_approx(
            left_moment, -30.0, "Fixed-end hogging moment at x=0 (kN.m)", abs_tol=0.01
        )

    def test_fixed_fixed_mid_span_sagging_extreme(
        self, fixed_fixed_beam: RectangularBeam
    ) -> None:
        """Fixed-fixed beam mid-span segment has sagging extreme at x=300 (kN.m = 15)."""
        beam = fixed_fixed_beam
        extremes = bending_moment_extremes_per_segment(
            beam.bending_moment_expression,
            beam.shear_force_expression,
            0.0,
            float(beam._x1),  # type: ignore[attr-defined]
        )
        mid_x, mid_moment = extremes[1]
        assert_approx(
            mid_x, 300.0, "Mid-span sagging extreme position (cm)", abs_tol=0.01
        )
        assert_approx(mid_moment, 15.0, "Mid-span sagging moment (kN.m)", abs_tol=0.01)

    def test_propped_cantilever_left_segment_extreme_at_fixed_end(
        self, propped_cantilever_beam: RectangularBeam
    ) -> None:
        """Propped cantilever: first segment [0, 149] extreme is the fixed-end moment.

        The left boundary (x=0) is NOT in the zeros list — the unconditional
        pad is what creates this segment. The extreme there is the hogging
        fixed-end moment.
        """
        beam = propped_cantilever_beam
        extremes = bending_moment_extremes_per_segment(
            beam.bending_moment_expression,
            beam.shear_force_expression,
            0.0,
            float(beam._x1),  # type: ignore[attr-defined]
        )
        left_x, left_moment = extremes[0]
        assert_approx(
            left_x, 0.0, "First segment extreme must be at x=0 (fixed end, cm)"
        )
        assert_approx(
            left_moment, -44.7316, "Fixed-end hogging moment (kN.m)", abs_tol=0.01
        )


# ---------------------------------------------------------------------------
# TestPositionsForBendingMoment
# ---------------------------------------------------------------------------


class TestPositionsForBendingMoment:
    """Tests for ``positions_for_bending_moment``."""

    def test_reachable_target_returns_sorted_positions(
        self, simply_supported_two_span_beam: RectangularBeam
    ) -> None:
        """Target M = 5.0 kN.m is reached at four positions in the two-span beam."""
        beam = simply_supported_two_span_beam
        positions = positions_for_bending_moment(
            beam.bending_moment_expression,
            5.0,
            0.0,
            float(beam._x1),  # type: ignore[attr-defined]
        )
        assert len(positions) == 4, (
            "M=5.0 kN.m is reached at 4 positions in the symmetric two-span beam"
        )
        assert positions == sorted(positions), (
            "Positions must be returned in sorted order"
        )
        assert_approx(positions[0], 59.9488, "First crossing of M=5 (cm)", abs_tol=0.01)
        assert_approx(
            positions[1], 166.8090, "Second crossing of M=5 (cm)", abs_tol=0.01
        )
        assert_approx(
            positions[2], 433.1910, "Third crossing of M=5 (cm)", abs_tol=0.01
        )
        assert_approx(
            positions[3], 540.0512, "Fourth crossing of M=5 (cm)", abs_tol=0.01
        )

    def test_unreachable_target_returns_empty_list(
        self, simply_supported_two_span_beam: RectangularBeam
    ) -> None:
        """Target that exceeds the maximum |M| returns an empty list."""
        beam = simply_supported_two_span_beam
        positions = positions_for_bending_moment(
            beam.bending_moment_expression,
            99.0,
            0.0,
            float(beam._x1),  # type: ignore[attr-defined]
        )
        assert positions == [], "An unreachable target moment should return []"

    def test_target_equal_to_extreme_returns_single_position(
        self, propped_cantilever_beam: RectangularBeam
    ) -> None:
        """Target equal to the hogging fixed-end moment returns exactly x = 0."""
        beam = propped_cantilever_beam
        # M(0) = -44.7316 kN.m for this configuration
        positions = positions_for_bending_moment(
            beam.bending_moment_expression,
            -20.0,
            0.0,
            float(beam._x1),  # type: ignore[attr-defined]
        )
        assert len(positions) == 1, (
            "M=-20 kN.m is reached at exactly one position in the propped cantilever"
        )
        assert_approx(
            positions[0], 73.1783, "Position where M = -20 kN.m (cm)", abs_tol=0.01
        )

    def test_negative_target_in_hogging_region(
        self, fixed_fixed_beam: RectangularBeam
    ) -> None:
        """Hogging target is reached symmetrically near both fixed ends."""
        beam = fixed_fixed_beam
        positions = positions_for_bending_moment(
            beam.bending_moment_expression,
            -25.0,
            0.0,
            float(beam._x1),  # type: ignore[attr-defined]
        )
        assert len(positions) == 2, (
            "M=-25 kN.m should be reached twice (once near each fixed end)"
        )
        assert positions == sorted(positions), "Positions must be sorted"
        # By symmetry, the two positions sum to 600 cm
        assert_approx(
            positions[0] + positions[1],
            600.0,
            "Symmetric positions sum to beam length (cm)",
        )
