"""Unit tests for src.data.nbr6120_2019.table_7.model (FillMaterial, Table7)."""

import pytest

from src.data.nbr6120_2019.table_7.data import TABLE_7
from src.data.nbr6120_2019.table_7.model import FillMaterial, Table7
from src.errors import TableLookupError

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def table() -> Table7:
    """Return the real Table7 (fills) singleton."""
    return TABLE_7


# ---------------------------------------------------------------------------
# Table7.find_material
# ---------------------------------------------------------------------------


class TestTable7FindMaterial:
    """Tests for Table7.find_material."""

    def test_partial_match_returns_correct_material(self, table: Table7) -> None:
        """Partial case-insensitive match returns the expected FillMaterial."""
        result = table.find_material("debris")
        assert "debris" in result.description.lower(), (
            "result description should contain 'debris'"
        )

    def test_match_is_case_insensitive(self, table: Table7) -> None:
        """Match is case-insensitive."""
        result_lower = table.find_material("expanded clay")
        result_upper = table.find_material("EXPANDED CLAY")
        assert result_lower == result_upper, "match should be case-insensitive"

    def test_no_match_raises_key_error(self, table: Table7) -> None:
        """A description that matches nothing raises KeyError."""
        with pytest.raises(TableLookupError):
            table.find_material("nonexistent fill material xyz")

    def test_none_min_max_for_single_value_material(self, table: Table7) -> None:
        """A single-value material has weight_min=None and weight_max=None."""
        result = table.find_material("debris")
        assert result.weight_min is None, "debris should have weight_min=None"
        assert result.weight_max is None, "debris should have weight_max=None"

    def test_range_material_has_min_and_max(self, table: Table7) -> None:
        """A range material exposes non-None weight_min and weight_max."""
        result = table.find_material("expanded clay")
        assert result.weight_min is not None, "expanded clay should have a weight_min"
        assert result.weight_max is not None, "expanded clay should have a weight_max"

    def test_returned_material_is_fill_material_instance(self, table: Table7) -> None:
        """find_material returns a FillMaterial instance."""
        result = table.find_material("soil")
        assert isinstance(result, FillMaterial), "result should be a FillMaterial"
