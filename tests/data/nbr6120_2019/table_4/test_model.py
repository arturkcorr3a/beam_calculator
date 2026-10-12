"""Unit tests for src.data.nbr6120_2019.table_4.model (CoveringMaterial, Table4)."""

import pytest

from src.data.nbr6120_2019.table_4.data import TABLE_4
from src.data.nbr6120_2019.table_4.model import Table4

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def table() -> Table4:
    """Return the real Table4 singleton."""
    return TABLE_4


# ---------------------------------------------------------------------------
# CoveringMaterial.get_weight
# ---------------------------------------------------------------------------


class TestCoveringMaterialGetWeight:
    """Tests for CoveringMaterial.get_weight."""

    def test_match_by_thickness_cm_returns_weight(self, table: Table4) -> None:
        """get_weight(0.3) returns the weight for a 0.3 cm ThicknessWeight entry."""
        material = table.find_material("asphalt felt")
        result = material.get_weight(0.3)
        expected = next(
            tw.weight for tw in material.thicknesses if tw.thickness_cm == 0.3
        )
        assert result == expected, (
            "get_weight(0.3) should return the weight for thickness_cm=0.3"
        )

    def test_default_none_thickness_returns_weight(self, table: Table4) -> None:
        """get_weight() (no arg, defaults to None) returns the weight for a None-thickness entry."""
        material = table.find_material("steel plates")
        result = material.get_weight()  # no thickness_cm
        expected = material.thicknesses[0].weight  # only one entry, thickness_cm=None
        assert result == expected, (
            "get_weight() should return weight for thickness_cm=None entry"
        )

    def test_polypropylene_raised_floor_none_thickness(self, table: Table4) -> None:
        """Polypropylene raised floor also uses the None-thickness lookup."""
        material = table.find_material("polypropylene")
        result = material.get_weight()
        expected = material.thicknesses[0].weight
        assert result == expected, (
            "polypropylene raised floor get_weight() should match None entry"
        )

    def test_float_drifted_thickness_matches(self, table: Table4) -> None:
        """A thickness_cm off by float drift (0.1 + 0.2) still matches the 0.3 cm entry."""
        material = table.find_material("asphalt felt")
        drifted = 0.1 + 0.2  # 0.30000000000000004
        result = material.get_weight(drifted)
        assert result == material.get_weight(0.3), (
            "a float-drifted 0.3 cm query should return the 0.3 cm weight"
        )

    def test_thickness_query_does_not_match_none_entry(self, table: Table4) -> None:
        """A numeric thickness never matches an entry without a thickness."""
        material = table.find_material("steel plates")  # only a None-thickness entry
        with pytest.raises(ValueError):
            material.get_weight(0.3)

    def test_missing_thickness_raises_value_error(self, table: Table4) -> None:
        """A thickness_cm not in the entry raises ValueError."""
        material = table.find_material("asphalt felt")
        with pytest.raises(ValueError):
            material.get_weight(99.9)


# ---------------------------------------------------------------------------
# Table4.find_material
# ---------------------------------------------------------------------------


class TestTable4FindMaterial:
    """Tests for Table4.find_material."""

    def test_partial_case_insensitive_match(self, table: Table4) -> None:
        """Partial case-insensitive description returns the matching CoveringMaterial."""
        result = table.find_material("asphalt felt")
        assert "asphalt felt" in result.description.lower(), (
            "result description should contain 'asphalt felt'"
        )

    def test_match_is_case_insensitive(self, table: Table4) -> None:
        """Match ignores case."""
        result_lower = table.find_material("residential")
        result_upper = table.find_material("RESIDENTIAL")
        assert result_lower == result_upper, "match should be case-insensitive"

    def test_no_match_raises_key_error(self, table: Table4) -> None:
        """Description that matches nothing raises KeyError."""
        with pytest.raises(KeyError):
            table.find_material("nonexistent material xyz")

    def test_first_match_is_returned(self, table: Table4) -> None:
        """The first matching entry is returned (order-sensitive)."""
        result = table.find_material("floor coverings")
        assert result == table.materials[3], (
            "first match for 'floor coverings' should be the residential/commercial entry (index 3)"
        )
