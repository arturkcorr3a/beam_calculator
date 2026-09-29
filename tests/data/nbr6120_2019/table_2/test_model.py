"""Unit tests for src.data.nbr6120_2019.table_2.model (Thickness, MasonryType, Table2)."""

import pytest

from src.data.nbr6120_2019.table_2.data import TABLE_2
from src.data.nbr6120_2019.table_2.model import Table2, Thickness

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def table() -> Table2:
    """Return the real Table2 singleton."""
    return TABLE_2


@pytest.fixture
def solid_ceramic_brick() -> object:
    """Return the 'Solid ceramic brick' structural masonry type."""
    return TABLE_2.find_masonry_type("Solid ceramic brick", structural=True)


@pytest.fixture
def glass_block() -> Thickness:
    """Return the glass block Thickness entry (has None for 1 cm and 2 cm coating)."""
    masonry = TABLE_2.find_masonry_type("Glass block", structural=False)
    return masonry.thicknesses[0]  # Thickness(8.0, 0.8, None, None)


# ---------------------------------------------------------------------------
# Thickness.get_weight
# ---------------------------------------------------------------------------


class TestThicknessGetWeight:
    """Tests for Thickness.get_weight."""

    def test_zero_coating_returns_zero_cm_weight(
        self, solid_ceramic_brick: object
    ) -> None:
        """0 cm coating returns the zero_cm weight."""
        from src.data.nbr6120_2019.table_2.model import MasonryType

        masonry = solid_ceramic_brick
        assert isinstance(masonry, MasonryType)
        thickness = masonry.get_thickness(9.0)
        result = thickness.get_weight(0)
        assert result == thickness.zero_cm, "0 cm coating should return zero_cm"

    def test_one_cm_coating_returns_one_cm_weight(
        self, solid_ceramic_brick: object
    ) -> None:
        """1 cm coating returns the one_cm weight."""
        from src.data.nbr6120_2019.table_2.model import MasonryType

        masonry = solid_ceramic_brick
        assert isinstance(masonry, MasonryType)
        thickness = masonry.get_thickness(9.0)
        result = thickness.get_weight(1)
        assert result == thickness.one_cm, "1 cm coating should return one_cm"

    def test_two_cm_coating_returns_two_cm_weight(
        self, solid_ceramic_brick: object
    ) -> None:
        """2 cm coating returns the two_cm weight."""
        from src.data.nbr6120_2019.table_2.model import MasonryType

        masonry = solid_ceramic_brick
        assert isinstance(masonry, MasonryType)
        thickness = masonry.get_thickness(9.0)
        result = thickness.get_weight(2)
        assert result == thickness.two_cm, "2 cm coating should return two_cm"

    def test_invalid_coating_raises_value_error(
        self, solid_ceramic_brick: object
    ) -> None:
        """Coating value outside {0, 1, 2} raises ValueError."""
        from src.data.nbr6120_2019.table_2.model import MasonryType

        masonry = solid_ceramic_brick
        assert isinstance(masonry, MasonryType)
        thickness = masonry.get_thickness(9.0)
        with pytest.raises(ValueError, match="0, 1, or 2"):
            thickness.get_weight(3)

    def test_none_weight_at_one_cm_raises_value_error(
        self, glass_block: Thickness
    ) -> None:
        """1 cm coating on glass block (None weight) raises ValueError."""
        with pytest.raises(ValueError, match="not defined"):
            glass_block.get_weight(1)

    def test_none_weight_at_two_cm_raises_value_error(
        self, glass_block: Thickness
    ) -> None:
        """2 cm coating on glass block (None weight) raises ValueError."""
        with pytest.raises(ValueError, match="not defined"):
            glass_block.get_weight(2)


# ---------------------------------------------------------------------------
# MasonryType.get_thickness
# ---------------------------------------------------------------------------


class TestMasonryTypeGetThickness:
    """Tests for MasonryType.get_thickness."""

    def test_existing_nominal_thickness_returned(self, table: Table2) -> None:
        """An exact nominal_cm match returns that Thickness entry."""
        masonry = table.find_masonry_type("Solid ceramic brick", structural=True)
        result = masonry.get_thickness(14.0)
        assert result.nominal_cm == 14.0, (
            "returned Thickness should have nominal_cm == 14.0"
        )

    def test_missing_nominal_thickness_raises_value_error(self, table: Table2) -> None:
        """A nominal_cm not in the entry raises ValueError."""
        masonry = table.find_masonry_type("Solid ceramic brick", structural=True)
        with pytest.raises(ValueError):
            masonry.get_thickness(999.0)


# ---------------------------------------------------------------------------
# Table2.find_masonry_type
# ---------------------------------------------------------------------------


class TestTable2FindMasonryType:
    """Tests for Table2.find_masonry_type."""

    def test_finds_structural_masonry_by_partial_match(self, table: Table2) -> None:
        """Partial case-insensitive match returns the correct structural masonry type."""
        result = table.find_masonry_type("hollow concrete block", structural=True)
        assert "Hollow concrete block" in result.type_description, (
            "should match the hollow concrete block structural masonry type"
        )

    def test_finds_non_bearing_masonry_by_partial_match(self, table: Table2) -> None:
        """Partial match returns a non-bearing masonry type when structural=False."""
        result = table.find_masonry_type("glass block", structural=False)
        assert "Glass block" in result.type_description, (
            "should match the glass block non-bearing masonry type"
        )

    def test_structural_flag_separates_lists(self, table: Table2) -> None:
        """structural=True searches structural list; structural=False searches non-bearing list."""
        # Glass block is only in non-bearing list
        with pytest.raises(KeyError):
            table.find_masonry_type("Glass block", structural=True)

    def test_match_is_case_insensitive(self, table: Table2) -> None:
        """Match is case-insensitive."""
        result_lower = table.find_masonry_type("solid ceramic brick", structural=True)
        result_upper = table.find_masonry_type("SOLID CERAMIC BRICK", structural=True)
        assert result_lower == result_upper, "match should be case-insensitive"

    def test_no_match_raises_key_error(self, table: Table2) -> None:
        """Description that matches nothing raises KeyError."""
        with pytest.raises(KeyError):
            table.find_masonry_type("nonexistent material xyz", structural=True)

    def test_first_match_returned_when_multiple_candidates(self, table: Table2) -> None:
        """Returns the first masonry type whose description contains the query string."""
        # "hollow concrete block" appears as both structural and non-bearing entries
        result_structural = table.find_masonry_type("hollow concrete", structural=True)
        result_non_bearing = table.find_masonry_type(
            "hollow concrete", structural=False
        )
        # Both should be different entries from their respective lists
        assert result_structural in table.structural_masonry, (
            "structural result should come from structural_masonry list"
        )
        assert result_non_bearing in table.non_bearing_masonry, (
            "non-bearing result should come from non_bearing_masonry list"
        )
