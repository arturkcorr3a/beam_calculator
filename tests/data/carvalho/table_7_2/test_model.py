"""Unit tests for src.data.carvalho.table_7_2.model (Table72 and SlabDeflectionEntry)."""

import math

import pytest

from src.data.carvalho.table_7_2.data import TABLE_7_2
from src.data.carvalho.table_7_2.model import Table72
from src.pavement_elements.slab_edge import Edges
from tests.helpers import assert_approx

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def table() -> Table72:
    """Return the real Table72 singleton."""
    return TABLE_7_2


# ---------------------------------------------------------------------------
# SlabDeflectionEntry.get_alpha
# ---------------------------------------------------------------------------


class TestSlabDeflectionEntryGetAlpha:
    """Tests for SlabDeflectionEntry.get_alpha."""

    @pytest.mark.parametrize(
        "case", list(range(1, 10)), ids=[f"case-{i}" for i in range(1, 10)]
    )
    def test_valid_cases_return_stored_coefficient(
        self, table: Table72, case: int
    ) -> None:
        """Each valid case returns the corresponding stored alpha from the entry."""
        entry = table.entries[0]
        result = entry.get_alpha(case)
        assert result == entry.cases[case - 1], (
            f"get_alpha({case}) should return cases[{case - 1}]"
        )

    def test_case_zero_raises_value_error(self, table: Table72) -> None:
        """Case 0 raises ValueError."""
        entry = table.entries[0]
        with pytest.raises(ValueError, match="1 and 9"):
            entry.get_alpha(0)

    def test_case_ten_raises_value_error(self, table: Table72) -> None:
        """Case 10 raises ValueError."""
        entry = table.entries[0]
        with pytest.raises(ValueError, match="1 and 9"):
            entry.get_alpha(10)


# ---------------------------------------------------------------------------
# Table72.get_alpha — exact match
# ---------------------------------------------------------------------------


class TestTable72GetAlphaExactMatch:
    """Tests for Table72.get_alpha with an exact aspect-ratio node."""

    def test_exact_match_first_entry(self, table: Table72) -> None:
        """Exact match at the first entry (1.00) returns that entry's stored alpha."""
        entry = table.entries[0]  # aspect_ratio == 1.00
        result = table.get_alpha(1.00, case=1)
        assert result == entry.cases[0], (
            "exact match at 1.00 should return entries[0].cases[0]"
        )

    def test_exact_match_second_entry(self, table: Table72) -> None:
        """Exact match at the second entry (1.05) returns that entry's stored alpha."""
        entry = table.entries[1]  # aspect_ratio == 1.05
        result = table.get_alpha(1.05, case=4)
        assert result == entry.cases[3], (
            "exact match at 1.05 should return entries[1].cases[3]"
        )


# ---------------------------------------------------------------------------
# Table72.get_alpha — interpolation
# ---------------------------------------------------------------------------


class TestTable72GetAlphaInterpolation:
    """Tests for Table72.get_alpha linear interpolation."""

    def test_midpoint_lambda_interpolates_linearly(self, table: Table72) -> None:
        """λ=1.025 (midpoint between 1.00 and 1.05) yields the linear blend of both entries."""
        lower = table.entries[0]  # aspect_ratio == 1.00
        upper = table.entries[1]  # aspect_ratio == 1.05
        t = (1.025 - lower.aspect_ratio) / (upper.aspect_ratio - lower.aspect_ratio)
        case = 1
        alpha_lower = lower.get_alpha(case)
        alpha_upper = upper.get_alpha(case)
        expected = alpha_lower + t * (alpha_upper - alpha_lower)

        result = table.get_alpha(1.025, case=case)
        assert_approx(result, expected, "interpolated alpha at λ=1.025 case 1")

    def test_interpolation_arbitrary_lambda(self, table: Table72) -> None:
        """λ=1.07 interpolates correctly between the 1.05 and 1.10 entries."""
        lower = table.entries[1]  # aspect_ratio == 1.05
        upper = table.entries[2]  # aspect_ratio == 1.10
        t = (1.07 - lower.aspect_ratio) / (upper.aspect_ratio - lower.aspect_ratio)
        case = 9
        alpha_lower = lower.get_alpha(case)
        alpha_upper = upper.get_alpha(case)
        expected = alpha_lower + t * (alpha_upper - alpha_lower)

        result = table.get_alpha(1.07, case=case)
        assert_approx(result, expected, "interpolated alpha at λ=1.07 case 9")


# ---------------------------------------------------------------------------
# Table72.get_alpha — infinity (beam) entry
# ---------------------------------------------------------------------------


class TestTable72GetAlphaInfEntry:
    """Tests for Table72.get_alpha with λ >= 2.0 (beam limit, inf entry)."""

    def test_lambda_above_two_uses_inf_entry(self, table: Table72) -> None:
        """λ=2.5 (above 2.0, no exact match) falls through to the inf entry."""
        inf_entry = next(e for e in table.entries if math.isinf(e.aspect_ratio))
        result = table.get_alpha(2.5, case=1)
        assert result == inf_entry.cases[0], "λ=2.5 should use the inf entry for case 1"

    def test_lambda_large_uses_inf_entry(self, table: Table72) -> None:
        """λ=100.0 uses the inf entry."""
        inf_entry = next(e for e in table.entries if math.isinf(e.aspect_ratio))
        result = table.get_alpha(100.0, case=5)
        assert result == inf_entry.cases[4], (
            "λ=100.0 should use the inf entry for case 5"
        )


# ---------------------------------------------------------------------------
# Table72._validate_inputs (exercised via get_alpha)
# ---------------------------------------------------------------------------


class TestTable72ValidateInputs:
    """Tests for Table72 input validation."""

    def test_lambda_below_one_raises_value_error(self, table: Table72) -> None:
        """λ < 1.0 raises ValueError mentioning 'aspect ratio'."""
        with pytest.raises(ValueError, match="aspect ratio"):
            table.get_alpha(0.99, case=1)

    def test_lambda_zero_raises_value_error(self, table: Table72) -> None:
        """λ=0 raises ValueError."""
        with pytest.raises(ValueError, match="aspect ratio"):
            table.get_alpha(0.0, case=1)

    def test_invalid_case_zero_raises_value_error(self, table: Table72) -> None:
        """Case 0 raises ValueError."""
        with pytest.raises(ValueError, match="1 and 9"):
            table.get_alpha(1.0, case=0)

    def test_invalid_case_ten_raises_value_error(self, table: Table72) -> None:
        """Case 10 raises ValueError."""
        with pytest.raises(ValueError, match="1 and 9"):
            table.get_alpha(1.0, case=10)


# ---------------------------------------------------------------------------
# Table72.determine_supporting_case
# ---------------------------------------------------------------------------


class TestDetermineSupportingCase:
    """Tests for Table72.determine_supporting_case."""

    @pytest.mark.parametrize(
        "conditions,lx,ly,expected_case",
        [
            # Case 1: no fixed edges
            (
                {
                    Edges.BOTTOM: "pinned",
                    Edges.TOP: "pinned",
                    Edges.LEFT: "pinned",
                    Edges.RIGHT: "pinned",
                },
                100.0,
                100.0,
                1,
            ),
            # Case 2: one short edge fixed (ly >= lx → short edges are TOP/BOTTOM)
            (
                {
                    Edges.TOP: "fixed",
                    Edges.BOTTOM: "pinned",
                    Edges.LEFT: "pinned",
                    Edges.RIGHT: "pinned",
                },
                100.0,
                120.0,
                2,
            ),
            # Case 3: one long edge fixed (ly >= lx → long edges are LEFT/RIGHT)
            (
                {
                    Edges.LEFT: "fixed",
                    Edges.BOTTOM: "pinned",
                    Edges.TOP: "pinned",
                    Edges.RIGHT: "pinned",
                },
                100.0,
                120.0,
                3,
            ),
            # Case 4: two adjacent (one long + one short)
            (
                {
                    Edges.LEFT: "fixed",
                    Edges.BOTTOM: "fixed",
                    Edges.TOP: "pinned",
                    Edges.RIGHT: "pinned",
                },
                100.0,
                120.0,
                4,
            ),
            # Case 5: two opposite short edges fixed
            (
                {
                    Edges.TOP: "fixed",
                    Edges.BOTTOM: "fixed",
                    Edges.LEFT: "pinned",
                    Edges.RIGHT: "pinned",
                },
                100.0,
                120.0,
                5,
            ),
            # Case 6: two opposite long edges fixed
            (
                {
                    Edges.LEFT: "fixed",
                    Edges.RIGHT: "fixed",
                    Edges.TOP: "pinned",
                    Edges.BOTTOM: "pinned",
                },
                100.0,
                120.0,
                6,
            ),
            # Case 7: three fixed, pinned is a long edge
            (
                {
                    Edges.LEFT: "pinned",
                    Edges.RIGHT: "fixed",
                    Edges.TOP: "fixed",
                    Edges.BOTTOM: "fixed",
                },
                100.0,
                120.0,
                7,
            ),
            # Case 8: three fixed, pinned is a short edge
            (
                {
                    Edges.TOP: "pinned",
                    Edges.BOTTOM: "fixed",
                    Edges.LEFT: "fixed",
                    Edges.RIGHT: "fixed",
                },
                100.0,
                120.0,
                8,
            ),
            # Case 9: all fixed
            (
                {
                    Edges.TOP: "fixed",
                    Edges.BOTTOM: "fixed",
                    Edges.LEFT: "fixed",
                    Edges.RIGHT: "fixed",
                },
                100.0,
                100.0,
                9,
            ),
        ],
        ids=[
            "case-1-all-pinned",
            "case-2-one-short-fixed",
            "case-3-one-long-fixed",
            "case-4-adjacent",
            "case-5-opp-short",
            "case-6-opp-long",
            "case-7-three-fixed-pinned-long",
            "case-8-three-fixed-pinned-short",
            "case-9-all-fixed",
        ],
    )
    def test_returns_correct_case(
        self,
        conditions: dict[Edges, str],
        lx: float,
        ly: float,
        expected_case: int,
    ) -> None:
        """determine_supporting_case returns the expected case number."""
        result = Table72.determine_supporting_case(conditions, lx=lx, ly=ly)  # type: ignore[arg-type]
        assert result == expected_case, f"Expected case {expected_case}, got {result}"
