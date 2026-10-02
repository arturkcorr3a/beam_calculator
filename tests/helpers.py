"""Shared assertion helpers for the properties test suite."""

import pytest


def assert_approx(
    actual: float,
    expected: float,
    message: str,
    *,
    abs_tol: float = 1e-5,
) -> None:
    """Assert that a float equals an expected value within an absolute tolerance.

    Wraps ``pytest.approx`` so the single unavoidable type suppression lives here
    instead of at every call site.

    Args:
        actual: Value produced by the code under test.
        expected: Hardcoded reference value.
        message: Assertion message describing the expectation and its physical unit.
        abs_tol: Absolute tolerance for the comparison. Defaults to 1e-5 so that
            reference values hardcoded to 5-decimal precision compare cleanly.
    """
    assert actual == pytest.approx(expected, abs=abs_tol), message  # type: ignore[reportUnknownMemberType]


def centroid_preserving_beam_width(thickness: float) -> float:
    """Return the widest supporting beam that keeps a slab's effective span unchanged

    With a_i = min(t_i / 2, 0.3 h), any beam width t <= 0.6 h makes a_i = t / 2, so
    the effective span equals the distance between the beam centerlines. The
    widest such width is returned, so test slabs keep their centroid geometry
    while the beams still have a physical width. The equality also holds for any
    thickness greater than the given one.

    Args:
        thickness: Slab thickness h (cm).

    Returns:
        Beam width (cm).

    References:
        ABNT NBR 6118:2014 — Section 14.7.2.2
    """
    return 0.6 * thickness
