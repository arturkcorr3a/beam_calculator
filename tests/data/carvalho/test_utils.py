"""Unit tests for src.data.carvalho.utils (find_bracket_and_fraction)."""

import types
from typing import cast

import pytest

from src.data.carvalho.utils import HasAspectRatio, find_bracket_and_fraction
from tests.helpers import assert_approx

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _entry(ar: float) -> HasAspectRatio:
    """Return a minimal HasAspectRatio double with the given aspect_ratio."""
    return cast(HasAspectRatio, types.SimpleNamespace(aspect_ratio=ar))


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


class TestFindBracketAndFraction:
    """Tests for find_bracket_and_fraction."""

    def test_returns_correct_bracket_interior(self) -> None:
        """Returns the two entries that bracket an interior lambda_val."""
        entries = [_entry(1.0), _entry(1.5), _entry(2.0)]
        lower, upper, _ = find_bracket_and_fraction(entries, 1.3)
        assert lower.aspect_ratio == 1.0, "lower bracket should be the 1.0 entry"
        assert upper.aspect_ratio == 1.5, "upper bracket should be the 1.5 entry"

    def test_fraction_midpoint(self) -> None:
        """Fraction is 0.5 when lambda_val is exactly between two entries."""
        entries = [_entry(1.0), _entry(2.0)]
        _, _, t = find_bracket_and_fraction(entries, 1.5)
        assert_approx(t, 0.5, "fraction at midpoint should be 0.5")

    def test_fraction_at_lower_boundary(self) -> None:
        """Fraction is 0 when lambda_val equals the lower entry's aspect_ratio."""
        entries = [_entry(1.0), _entry(2.0)]
        lower, _, t = find_bracket_and_fraction(entries, 1.0)
        assert lower.aspect_ratio == 1.0, "lower entry should match the requested value"
        assert_approx(t, 0.0, "fraction at lower boundary should be 0.0")

    def test_fraction_calculation(self) -> None:
        """Fraction equals (lambda_val - lower) / (upper - lower)."""
        entries = [_entry(1.0), _entry(1.5), _entry(2.0)]
        _, _, t = find_bracket_and_fraction(entries, 1.2)
        expected_t = (1.2 - 1.0) / (1.5 - 1.0)
        assert_approx(
            t, expected_t, "fraction should equal (lambda - lower) / (upper - lower)"
        )

    def test_out_of_range_lambda_raises_index_error(self) -> None:
        """Raises IndexError when lambda_val exceeds the last entry (no bracket available)."""
        entries = [_entry(1.0), _entry(1.5), _entry(2.0)]
        with pytest.raises(IndexError):
            find_bracket_and_fraction(entries, 3.0)

    def test_single_element_raises_index_error(self) -> None:
        """Raises IndexError when given a single-element sequence (no bracket possible)."""
        entries = [_entry(1.0)]
        with pytest.raises(IndexError):
            find_bracket_and_fraction(entries, 1.5)

    def test_duplicate_aspect_ratio_raises_zero_division(self) -> None:
        """Raises ZeroDivisionError when adjacent entries share the same aspect_ratio."""
        entries = [_entry(1.0), _entry(1.0), _entry(2.0)]
        with pytest.raises(ZeroDivisionError):
            find_bracket_and_fraction(entries, 1.0)
