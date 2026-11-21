"""Unit tests for src.data.carvalho.table_7.model (Table7 and SlabMomentEntry)."""

import pytest

from src.data.carvalho.table_7.data import TABLE_7
from src.data.carvalho.table_7.model import Table7
from src.errors import EnginePreconditionError
from src.pavement_elements.slab_edge import Edges
from tests.helpers import assert_approx

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def table() -> Table7:
    """Return the real Table7 singleton."""
    return TABLE_7


# ---------------------------------------------------------------------------
# SlabMomentEntry.get_mu
# ---------------------------------------------------------------------------


class TestSlabMomentEntryGetMu:
    """Tests for SlabMomentEntry.get_mu."""

    def test_case_one_returns_first_coefficients(self, table: Table7) -> None:
        """Case 1 returns the first MomentCoefficients of the entry."""
        entry = table.entries[0]
        result = entry.get_mu(1)
        assert result == entry.cases[0], "case 1 should return cases[0]"

    @pytest.mark.parametrize(
        "case", list(range(1, 10)), ids=[f"case-{i}" for i in range(1, 10)]
    )
    def test_valid_cases_return_stored_coefficient(
        self, table: Table7, case: int
    ) -> None:
        """Each valid case returns the corresponding stored MomentCoefficients."""
        entry = table.entries[0]
        result = entry.get_mu(case)
        assert result == entry.cases[case - 1], (
            f"get_mu({case}) should return cases[{case - 1}]"
        )

    def test_case_zero_raises_value_error(self, table: Table7) -> None:
        """Case 0 raises ValueError."""
        entry = table.entries[0]
        with pytest.raises(EnginePreconditionError, match="1 and 9"):
            entry.get_mu(0)

    def test_case_ten_raises_value_error(self, table: Table7) -> None:
        """Case 10 raises ValueError."""
        entry = table.entries[0]
        with pytest.raises(EnginePreconditionError, match="1 and 9"):
            entry.get_mu(10)


# ---------------------------------------------------------------------------
# SlabMomentEntry.get_mu_x / get_mu_y delegation
# ---------------------------------------------------------------------------


class TestSlabMomentEntryDelegation:
    """Tests for SlabMomentEntry.get_mu_x and get_mu_y."""

    def test_get_mu_x_matches_get_mu_mu_x(self, table: Table7) -> None:
        """get_mu_x(case) == get_mu(case).mu_x."""
        entry = table.entries[0]
        for case in range(1, 10):
            assert entry.get_mu_x(case) == entry.get_mu(case).mu_x, (
                f"get_mu_x({case}) should equal get_mu({case}).mu_x"
            )

    def test_get_mu_y_matches_get_mu_mu_y(self, table: Table7) -> None:
        """get_mu_y(case) == get_mu(case).mu_y."""
        entry = table.entries[0]
        for case in range(1, 10):
            assert entry.get_mu_y(case) == entry.get_mu(case).mu_y, (
                f"get_mu_y({case}) should equal get_mu({case}).mu_y"
            )


# ---------------------------------------------------------------------------
# Table7.get_mu — exact match
# ---------------------------------------------------------------------------


class TestTable7GetMuExactMatch:
    """Tests for Table7.get_mu with an exact aspect-ratio node."""

    def test_exact_match_returns_entry_value(self, table: Table7) -> None:
        """Exact aspect-ratio match returns that entry's stored coefficients."""
        entry = table.entries[0]  # aspect_ratio == 1.00
        result = table.get_mu(1.00, case=1)
        assert result == entry.cases[0], (
            "exact match at 1.00 should return entries[0].cases[0]"
        )

    def test_exact_match_second_entry(self, table: Table7) -> None:
        """Exact match at the second entry (1.05) returns that entry's value."""
        entry = table.entries[1]  # aspect_ratio == 1.05
        result = table.get_mu(1.05, case=2)
        assert result == entry.cases[1], (
            "exact match at 1.05 should return entries[1].cases[1]"
        )


# ---------------------------------------------------------------------------
# Table7.get_mu — interpolation
# ---------------------------------------------------------------------------


class TestTable7GetMuInterpolation:
    """Tests for Table7.get_mu linear interpolation."""

    def test_midpoint_lambda_interpolates_linearly(self, table: Table7) -> None:
        """λ=1.025 (midpoint between 1.00 and 1.05) yields the linear blend of both entries."""
        lower = table.entries[0]  # aspect_ratio == 1.00
        upper = table.entries[1]  # aspect_ratio == 1.05
        t = (1.025 - lower.aspect_ratio) / (upper.aspect_ratio - lower.aspect_ratio)
        case = 1
        mu_lower = lower.get_mu(case)
        mu_upper = upper.get_mu(case)
        expected_mu_x = mu_lower.mu_x + t * (mu_upper.mu_x - mu_lower.mu_x)
        expected_mu_y = mu_lower.mu_y + t * (mu_upper.mu_y - mu_lower.mu_y)

        result = table.get_mu(1.025, case=case)
        assert_approx(result.mu_x, expected_mu_x, "interpolated mu_x at λ=1.025 case 1")
        assert_approx(result.mu_y, expected_mu_y, "interpolated mu_y at λ=1.025 case 1")

    def test_interpolation_off_midpoint(self, table: Table7) -> None:
        """λ=1.03 interpolates correctly between the 1.00 and 1.05 entries."""
        lower = table.entries[0]
        upper = table.entries[1]
        t = (1.03 - lower.aspect_ratio) / (upper.aspect_ratio - lower.aspect_ratio)
        case = 9
        mu_lower = lower.get_mu(case)
        mu_upper = upper.get_mu(case)
        expected_mu_x = mu_lower.mu_x + t * (mu_upper.mu_x - mu_lower.mu_x)

        result = table.get_mu(1.03, case=case)
        assert_approx(result.mu_x, expected_mu_x, "interpolated mu_x at λ=1.03 case 9")


# ---------------------------------------------------------------------------
# Table7.get_mu — infinity (beam) entry
# ---------------------------------------------------------------------------


class TestTable7GetMuInfEntry:
    """Tests for Table7.get_mu with λ >= 2.0 (beam limit, inf entry)."""

    def test_lambda_between_two_and_three_uses_inf_entry(self, table: Table7) -> None:
        """λ=2.5 (above 2.0, no exact match) falls through to the inf entry."""
        import math

        inf_entry = next(e for e in table.entries if math.isinf(e.aspect_ratio))
        result = table.get_mu(2.5, case=1)
        assert result == inf_entry.cases[0], "λ=2.5 should use the inf entry for case 1"

    def test_lambda_greater_than_two_uses_inf_entry(self, table: Table7) -> None:
        """λ=5.0 uses the inf entry."""
        import math

        inf_entry = next(e for e in table.entries if math.isinf(e.aspect_ratio))
        result = table.get_mu(5.0, case=3)
        assert result == inf_entry.cases[2], "λ=5.0 should use the inf entry for case 3"


# ---------------------------------------------------------------------------
# Table7._validate_inputs (private — exercised via get_mu)
# ---------------------------------------------------------------------------


class TestTable7ValidateInputs:
    """Tests for Table7 input validation."""

    def test_lambda_below_one_raises_value_error(self, table: Table7) -> None:
        """λ < 1.0 raises ValueError mentioning 'aspect ratio'."""
        with pytest.raises(EnginePreconditionError, match="aspect ratio"):
            table.get_mu(0.9, case=1)

    def test_lambda_zero_raises_value_error(self, table: Table7) -> None:
        """λ=0 raises ValueError."""
        with pytest.raises(EnginePreconditionError, match="aspect ratio"):
            table.get_mu(0.0, case=1)

    def test_invalid_case_raises_value_error(self, table: Table7) -> None:
        """Case 0 raises ValueError mentioning '1 and 9'."""
        with pytest.raises(EnginePreconditionError, match="1 and 9"):
            table.get_mu(1.0, case=0)

    def test_case_ten_raises_value_error(self, table: Table7) -> None:
        """Case 10 raises ValueError."""
        with pytest.raises(EnginePreconditionError, match="1 and 9"):
            table.get_mu(1.0, case=10)


# ---------------------------------------------------------------------------
# Table7.get_mu_x / get_mu_y convenience wrappers
# ---------------------------------------------------------------------------


class TestTable7ConvenienceWrappers:
    """Tests for Table7.get_mu_x and get_mu_y."""

    def test_get_mu_x_equals_get_mu_mu_x(self, table: Table7) -> None:
        """get_mu_x(lambda, case) == get_mu(lambda, case).mu_x."""
        result = table.get_mu_x(1.00, 1)
        expected = table.get_mu(1.00, 1).mu_x
        assert result == expected, "get_mu_x should equal get_mu(...).mu_x"

    def test_get_mu_y_equals_get_mu_mu_y(self, table: Table7) -> None:
        """get_mu_y(lambda, case) == get_mu(lambda, case).mu_y."""
        result = table.get_mu_y(1.00, 1)
        expected = table.get_mu(1.00, 1).mu_y
        assert result == expected, "get_mu_y should equal get_mu(...).mu_y"


# ---------------------------------------------------------------------------
# Table7.determine_supporting_case
# ---------------------------------------------------------------------------


class TestDetermineSupportingCase:
    """Tests for Table7.determine_supporting_case."""

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
                    Edges.BOTTOM: "fixed",
                    Edges.TOP: "pinned",
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
                    Edges.BOTTOM: "pinned",
                    Edges.TOP: "pinned",
                    Edges.LEFT: "fixed",
                    Edges.RIGHT: "pinned",
                },
                100.0,
                120.0,
                3,
            ),
            # Case 4: two adjacent edges fixed (one short + one long)
            (
                {
                    Edges.BOTTOM: "fixed",
                    Edges.TOP: "pinned",
                    Edges.LEFT: "fixed",
                    Edges.RIGHT: "pinned",
                },
                100.0,
                120.0,
                4,
            ),
            # Case 5: two opposite short edges fixed
            (
                {
                    Edges.BOTTOM: "fixed",
                    Edges.TOP: "fixed",
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
                    Edges.BOTTOM: "pinned",
                    Edges.TOP: "pinned",
                    Edges.LEFT: "fixed",
                    Edges.RIGHT: "fixed",
                },
                100.0,
                120.0,
                6,
            ),
            # Case 7: three fixed, pinned edge is a long edge (LEFT/RIGHT when ly >= lx)
            (
                {
                    Edges.BOTTOM: "fixed",
                    Edges.TOP: "fixed",
                    Edges.LEFT: "pinned",
                    Edges.RIGHT: "fixed",
                },
                100.0,
                120.0,
                7,
            ),
            # Case 8: three fixed, pinned edge is a short edge (TOP/BOTTOM when ly >= lx)
            (
                {
                    Edges.BOTTOM: "pinned",
                    Edges.TOP: "fixed",
                    Edges.LEFT: "fixed",
                    Edges.RIGHT: "fixed",
                },
                100.0,
                120.0,
                8,
            ),
            # Case 9: all four edges fixed
            (
                {
                    Edges.BOTTOM: "fixed",
                    Edges.TOP: "fixed",
                    Edges.LEFT: "fixed",
                    Edges.RIGHT: "fixed",
                },
                100.0,
                100.0,
                9,
            ),
            # Case 2 when ly < lx: short edges become LEFT/RIGHT
            (
                {
                    Edges.BOTTOM: "pinned",
                    Edges.TOP: "pinned",
                    Edges.LEFT: "fixed",
                    Edges.RIGHT: "pinned",
                },
                150.0,
                100.0,
                2,
            ),
            # Case 3 when ly < lx: long edges become TOP/BOTTOM
            (
                {
                    Edges.BOTTOM: "fixed",
                    Edges.TOP: "pinned",
                    Edges.LEFT: "pinned",
                    Edges.RIGHT: "pinned",
                },
                150.0,
                100.0,
                3,
            ),
        ],
        ids=[
            "case-1-no-fixed",
            "case-2-one-short-fixed-ly-gte-lx",
            "case-3-one-long-fixed-ly-gte-lx",
            "case-4-two-adjacent",
            "case-5-two-opp-short",
            "case-6-two-opp-long",
            "case-7-three-fixed-pinned-long",
            "case-8-three-fixed-pinned-short",
            "case-9-all-fixed",
            "case-2-one-short-fixed-ly-lt-lx",
            "case-3-one-long-fixed-ly-lt-lx",
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
        result = Table7.determine_supporting_case(conditions, lx=lx, ly=ly)  # type: ignore[arg-type]
        assert result == expected_case, (
            f"Expected case {expected_case} but got {result} for conditions={conditions}, lx={lx}, ly={ly}"
        )
