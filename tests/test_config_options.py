"""Unit tests for the AppConfig option enums and their persisted values."""

from src.config_options import Aggregate, ExposureClass, OccupancyCategory
from src.data.nbr6120_2019.table_10.data import TABLE_10


class TestOccupancyCategory:
    """Tests keeping OccupancyCategory in sync with NBR 6120 Table 10."""

    def test_values_match_table_10_categories(self) -> None:
        enum_values = {category.value for category in OccupancyCategory}
        table_descriptions = {category.description for category in TABLE_10.categories}
        assert enum_values == table_descriptions, (
            "OccupancyCategory values should match TABLE_10 category descriptions "
            f"exactly; missing from enum: {table_descriptions - enum_values}, "
            f"not in table: {enum_values - table_descriptions}"
        )

    def test_every_member_resolves_to_its_own_category(self) -> None:
        for category in OccupancyCategory:
            found = TABLE_10.find_category(category.value)
            assert found.description == category.value, (
                f"find_category({category.value!r}) should resolve to that exact "
                f"category, got {found.description!r}"
            )


class TestExposureClass:
    """Tests pinning the persisted integer values of ExposureClass."""

    def test_values(self) -> None:
        values = [exposure_class.value for exposure_class in ExposureClass]
        assert values == [1, 2, 3, 4], (
            "ExposureClass values should be 1-4 (NBR 6118 Table 6.1)"
        )


class TestAggregate:
    """Tests pinning the persisted string values of Aggregate."""

    def test_values(self) -> None:
        values = {aggregate.value for aggregate in Aggregate}
        assert values == {
            "basalt",
            "diabase",
            "granite",
            "gneiss",
            "limestone",
            "sandstone",
        }, "Aggregate values should match the strings stored in saved files"
