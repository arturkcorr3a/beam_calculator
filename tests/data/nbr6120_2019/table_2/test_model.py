"""Unit tests for src.data.nbr6120_2019.table_2.model (Thickness, MasonryType, Table2)."""

import pytest

from src.data.nbr6120_2019.table_2.data import TABLE_2
from src.data.nbr6120_2019.table_2.model import Table2, Thickness
from src.errors import TableLookupError

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def table() -> Table2:
    """Return the real Table2 singleton."""
    return TABLE_2


@pytest.fixture
def hollow_concrete_block() -> object:
    """Return the 'Hollow concrete block' masonry type."""
    return TABLE_2.find_masonry_type("Hollow concrete block")


@pytest.fixture
def glass_block() -> Thickness:
    """Return the glass block Thickness entry (has None for 1 cm and 2 cm coating)."""
    masonry = TABLE_2.find_masonry_type("Glass block")
    return masonry.thicknesses[0]  # Thickness(8.0, 0.8, None, None)


# ---------------------------------------------------------------------------
# Thickness.get_weight
# ---------------------------------------------------------------------------


class TestThicknessGetWeight:
    """Tests for Thickness.get_weight."""

    def test_zero_coating_returns_zero_cm_weight(
        self, hollow_concrete_block: object
    ) -> None:
        """0 cm coating returns the zero_cm weight."""
        from src.data.nbr6120_2019.table_2.model import MasonryType

        masonry = hollow_concrete_block
        assert isinstance(masonry, MasonryType)
        thickness = masonry.get_thickness(9.0)
        result = thickness.get_weight(0)
        assert result == thickness.zero_cm, "0 cm coating should return zero_cm"

    def test_one_cm_coating_returns_one_cm_weight(
        self, hollow_concrete_block: object
    ) -> None:
        """1 cm coating returns the one_cm weight."""
        from src.data.nbr6120_2019.table_2.model import MasonryType

        masonry = hollow_concrete_block
        assert isinstance(masonry, MasonryType)
        thickness = masonry.get_thickness(9.0)
        result = thickness.get_weight(1)
        assert result == thickness.one_cm, "1 cm coating should return one_cm"

    def test_two_cm_coating_returns_two_cm_weight(
        self, hollow_concrete_block: object
    ) -> None:
        """2 cm coating returns the two_cm weight."""
        from src.data.nbr6120_2019.table_2.model import MasonryType

        masonry = hollow_concrete_block
        assert isinstance(masonry, MasonryType)
        thickness = masonry.get_thickness(9.0)
        result = thickness.get_weight(2)
        assert result == thickness.two_cm, "2 cm coating should return two_cm"

    def test_invalid_coating_raises_value_error(
        self, hollow_concrete_block: object
    ) -> None:
        """Coating value outside {0, 1, 2} raises ValueError."""
        from src.data.nbr6120_2019.table_2.model import MasonryType

        masonry = hollow_concrete_block
        assert isinstance(masonry, MasonryType)
        thickness = masonry.get_thickness(9.0)
        with pytest.raises(TableLookupError, match="0, 1, or 2"):
            thickness.get_weight(3)

    def test_none_weight_at_one_cm_raises_value_error(
        self, glass_block: Thickness
    ) -> None:
        """1 cm coating on glass block (None weight) raises ValueError."""
        with pytest.raises(TableLookupError, match="not defined"):
            glass_block.get_weight(1)

    def test_none_weight_at_two_cm_raises_value_error(
        self, glass_block: Thickness
    ) -> None:
        """2 cm coating on glass block (None weight) raises ValueError."""
        with pytest.raises(TableLookupError, match="not defined"):
            glass_block.get_weight(2)


# ---------------------------------------------------------------------------
# MasonryType.get_thickness
# ---------------------------------------------------------------------------


class TestMasonryTypeGetThickness:
    """Tests for MasonryType.get_thickness."""

    def test_existing_nominal_thickness_returned(self, table: Table2) -> None:
        """An exact nominal_cm match returns that Thickness entry."""
        masonry = table.find_masonry_type("Hollow concrete block")
        result = masonry.get_thickness(14.0)
        assert result.nominal_cm == 14.0, (
            "returned Thickness should have nominal_cm == 14.0"
        )

    def test_float_drifted_nominal_thickness_matches(self, table: Table2) -> None:
        """A nominal_cm off by float drift (0.14 m → cm) still matches the entry."""
        masonry = table.find_masonry_type("Hollow concrete block")
        drifted = 0.14 * 100  # 14.000000000000002
        result = masonry.get_thickness(drifted)
        assert result.nominal_cm == 14.0, (
            "a float-drifted 14 cm query should return the 14 cm entry"
        )

    def test_missing_nominal_thickness_raises_value_error(self, table: Table2) -> None:
        """A nominal_cm not in the entry raises ValueError."""
        masonry = table.find_masonry_type("Hollow concrete block")
        with pytest.raises(TableLookupError):
            masonry.get_thickness(999.0)


# ---------------------------------------------------------------------------
# Table2.find_masonry_type
# ---------------------------------------------------------------------------


class TestTable2FindMasonryType:
    """Tests for Table2.find_masonry_type."""

    def test_finds_masonry_by_partial_match(self, table: Table2) -> None:
        """Partial case-insensitive match returns the correct masonry type."""
        result = table.find_masonry_type("hollow concrete block")
        assert "Hollow concrete block" in result.type_description, (
            "should match the hollow concrete block masonry type"
        )

    def test_match_is_case_insensitive(self, table: Table2) -> None:
        """Match is case-insensitive."""
        result_lower = table.find_masonry_type("glass block")
        result_upper = table.find_masonry_type("GLASS BLOCK")
        assert result_lower == result_upper, "match should be case-insensitive"

    def test_structural_masonry_is_not_listed(self, table: Table2) -> None:
        """Structural-only masonry types are not part of the table."""
        with pytest.raises(TableLookupError):
            table.find_masonry_type("Solid ceramic brick")

    def test_no_match_raises_key_error(self, table: Table2) -> None:
        """Description that matches nothing raises KeyError."""
        with pytest.raises(TableLookupError):
            table.find_masonry_type("nonexistent material xyz")

    def test_first_match_returned_when_multiple_candidates(self, table: Table2) -> None:
        """Returns the first masonry type whose description contains the query string."""
        result = table.find_masonry_type("block")
        assert result is table.masonry[0], "should return the first matching entry"
