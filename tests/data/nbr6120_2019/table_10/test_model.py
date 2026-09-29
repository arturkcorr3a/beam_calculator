"""Unit tests for src.data.nbr6120_2019.table_10.model (BuildingCategory, Table10)."""

import pytest

from src.data.nbr6120_2019.table_10.data import TABLE_10
from src.data.nbr6120_2019.table_10.model import BuildingCategory, Table10
from tests.helpers import assert_approx

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def table() -> Table10:
    """Return the real Table10 singleton."""
    return TABLE_10


@pytest.fixture
def residential() -> BuildingCategory:
    """Return the 'Residential buildings' category."""
    return TABLE_10.find_category("Residential buildings")


@pytest.fixture
def helipads() -> BuildingCategory:
    """Return the 'Helipads' category (has no location entries)."""
    return TABLE_10.find_category("Helipads")


@pytest.fixture
def general_warehouses() -> BuildingCategory:
    """Return the 'General use warehouses' category (has no location entries)."""
    return TABLE_10.find_category("General use warehouses")


# ---------------------------------------------------------------------------
# BuildingCategory.get_location_load
# ---------------------------------------------------------------------------


class TestBuildingCategoryGetLocationLoad:
    """Tests for BuildingCategory.get_location_load."""

    def test_partial_match_returns_distributed_load(
        self, residential: BuildingCategory
    ) -> None:
        """Partial case-insensitive match returns the location's distributed_load."""
        result = residential.get_location_load("Bedrooms")
        expected = next(
            loc.distributed_load
            for loc in residential.locations
            if "Bedrooms" in loc.description
        )
        assert_approx(
            result,
            expected,
            "get_location_load('Bedrooms') should match the stored load",
        )

    def test_match_is_case_insensitive(self, residential: BuildingCategory) -> None:
        """Match ignores case."""
        result_lower = residential.get_location_load("bedrooms")
        result_upper = residential.get_location_load("BEDROOMS")
        assert result_lower == result_upper, "match should be case-insensitive"

    def test_no_match_raises_key_error(self, residential: BuildingCategory) -> None:
        """A description that matches nothing raises KeyError."""
        with pytest.raises(KeyError):
            residential.get_location_load("nonexistent location xyz")

    def test_empty_locations_helipads_always_raises(
        self, helipads: BuildingCategory
    ) -> None:
        """Helipads category has no locations; any query raises KeyError."""
        with pytest.raises(KeyError):
            helipads.get_location_load("landing pad")

    def test_empty_locations_warehouses_always_raises(
        self, general_warehouses: BuildingCategory
    ) -> None:
        """General use warehouses category has no locations; any query raises KeyError."""
        with pytest.raises(KeyError):
            general_warehouses.get_location_load("storage area")

    def test_first_match_returned_for_ambiguous_query(
        self, residential: BuildingCategory
    ) -> None:
        """First matching location is returned for an ambiguous query."""
        # "rooms" appears in "Bedrooms", "Living rooms...", "Party rooms...",
        # "Game rooms", "Storage rooms" — first should be "Bedrooms"
        result = residential.get_location_load("rooms")
        first_rooms_load = next(
            loc.distributed_load
            for loc in residential.locations
            if "rooms" in loc.description.lower()
        )
        assert_approx(
            result,
            first_rooms_load,
            "first matching 'rooms' location should be returned",
        )


# ---------------------------------------------------------------------------
# Table10.find_category
# ---------------------------------------------------------------------------


class TestTable10FindCategory:
    """Tests for Table10.find_category."""

    def test_partial_match_returns_correct_category(self, table: Table10) -> None:
        """Partial case-insensitive match returns the expected BuildingCategory."""
        result = table.find_category("Residential")
        assert "Residential" in result.description, (
            "result description should contain 'Residential'"
        )

    def test_match_is_case_insensitive(self, table: Table10) -> None:
        """Match ignores case."""
        result_lower = table.find_category("residential")
        result_upper = table.find_category("RESIDENTIAL")
        assert result_lower == result_upper, "match should be case-insensitive"

    def test_no_match_raises_key_error(self, table: Table10) -> None:
        """A description that matches nothing raises KeyError."""
        with pytest.raises(KeyError):
            table.find_category("nonexistent category xyz")

    def test_finds_helipads(self, table: Table10) -> None:
        """Helipads category is found by exact description substring."""
        result = table.find_category("Helipads")
        assert result.description == "Helipads", "should find the Helipads category"

    def test_finds_general_warehouses(self, table: Table10) -> None:
        """General use warehouses category is found by partial match."""
        result = table.find_category("General use warehouses")
        assert result.description == "General use warehouses", (
            "should find the General use warehouses category"
        )

    def test_returned_category_is_building_category_instance(
        self, table: Table10
    ) -> None:
        """find_category returns a BuildingCategory instance."""
        result = table.find_category("Residential")
        assert isinstance(result, BuildingCategory), (
            "result should be a BuildingCategory"
        )

    def test_first_match_returned_for_ambiguous_query(self, table: Table10) -> None:
        """First matching category in the tuple is returned."""
        # "buildings" appears in several categories; the first should be "Residential buildings"
        result = table.find_category("buildings")
        first_buildings = next(
            cat for cat in table.categories if "buildings" in cat.description.lower()
        )
        assert result == first_buildings, (
            "first category containing 'buildings' should be returned"
        )
