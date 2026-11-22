"""Unit tests for src.data.nbr6120_2019.table_8.model (CeilingDuctSprinklerMaterial, Table8)."""

import pytest

from src.data.nbr6120_2019.table_8.data import TABLE_8
from src.data.nbr6120_2019.table_8.model import CeilingDuctSprinklerMaterial, Table8
from src.errors import TableLookupError

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def table() -> Table8:
    """Return the real Table8 singleton."""
    return TABLE_8


# ---------------------------------------------------------------------------
# Table8.find_material
# ---------------------------------------------------------------------------


class TestTable8FindMaterial:
    """Tests for Table8.find_material."""

    def test_partial_match_returns_correct_material(self, table: Table8) -> None:
        """Partial case-insensitive match returns the expected material."""
        result = table.find_material("drywall")
        assert "Drywall" in result.description, (
            "result description should contain 'Drywall'"
        )

    def test_match_is_case_insensitive(self, table: Table8) -> None:
        """Match ignores case."""
        result_lower = table.find_material("drywall")
        result_upper = table.find_material("DRYWALL")
        assert result_lower == result_upper, "match should be case-insensitive"

    def test_no_match_raises_key_error(self, table: Table8) -> None:
        """A description that matches nothing raises KeyError."""
        with pytest.raises(TableLookupError):
            table.find_material("nonexistent ceiling xyz")

    def test_first_match_returned_for_ambiguous_query(self, table: Table8) -> None:
        """'ceiling' matches multiple descriptions; the first one in the list is returned."""
        # The table has several entries whose description contains "ceiling":
        # "Mineral fiber ceiling...", "Drywall ceiling...", "Plasterboard ceiling...",
        # "PVC ceiling...", "Aluminum plate ceiling...".
        # The first match should be the Mineral fiber ceiling.
        result = table.find_material("ceiling")
        assert result == table.materials[0], (
            "first match for 'ceiling' should be the Mineral fiber ceiling (index 0)"
        )

    def test_returned_material_is_correct_type(self, table: Table8) -> None:
        """find_material returns a CeilingDuctSprinklerMaterial instance."""
        result = table.find_material("drywall")
        assert isinstance(result, CeilingDuctSprinklerMaterial), (
            "result should be a CeilingDuctSprinklerMaterial"
        )

    def test_sprinkler_match_by_diameter(self, table: Table8) -> None:
        """Partial match on 'sprinkler' with '65 mm' returns the 65 mm sprinkler entry."""
        result = table.find_material("65 mm")
        assert "65 mm" in result.description, (
            "result description should mention '65 mm'"
        )

    def test_duct_partial_match(self, table: Table8) -> None:
        """Partial match on 'ventilation' returns a ventilation duct entry."""
        result = table.find_material("ventilation")
        assert "Ventilation" in result.description, (
            "result description should contain 'Ventilation'"
        )
