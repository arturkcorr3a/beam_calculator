"""Unit tests for the superficial (per-area) load calculations."""

import pytest

from src.config import APP_CONFIG
from src.loading.superficial_loads import SuperficialLoads
from tests.helpers import assert_approx

RESIDENTIAL_FLOOR = (
    "Floor coverings of residential and commercial buildings "
    "(gamma_{ap-m} = 20 kN/m³)"
)


class TestGetConcreteElementOwnWeight:
    """Tests for the own weight of a superficial concrete element in kN/m²."""

    def test_reinforced_thickness_0_20(self) -> None:
        expected_weight = 5.0  # kN/m² (25.0 kN/m³ * 0.20 m)
        assert (
            SuperficialLoads.get_concrete_element_own_weight(0.20, reinforced=True)
            == expected_weight
        ), "Reinforced 0.20 m slab should weigh 5.0 kN/m²"

    def test_plain_thickness_0_20(self) -> None:
        expected_weight = 4.8  # kN/m² (24.0 kN/m³ * 0.20 m)
        assert_approx(
            SuperficialLoads.get_concrete_element_own_weight(0.20, reinforced=False),
            expected_weight,
            "Plain 0.20 m slab should weigh 4.8 kN/m²",
        )


class TestGetInfillWeight:
    """Tests for the infill weight in kN/m²."""

    def test_construction_debris_8cm(self) -> None:
        # TABLE_7 "Construction debris, rubble" weight_avg -> 15.0 kN/m³
        expected_weight = 1.2  # kN/m² (15.0 kN/m³ * 0.08 m)
        assert_approx(
            SuperficialLoads.get_infill_weight("Construction debris, rubble", 8.0),
            expected_weight,
            "15.0 kN/m³ infill at 8 cm should give 1.2 kN/m²",
        )

    def test_empty_description_returns_zero(self) -> None:
        expected_weight = 0.0
        assert SuperficialLoads.get_infill_weight("", 8.0) == expected_weight, (
            "An empty infill description should return 0.0 kN/m²"
        )

    def test_zero_thickness_returns_zero(self) -> None:
        expected_weight = 0.0
        assert (
            SuperficialLoads.get_infill_weight("Construction debris, rubble", 0.0)
            == expected_weight
        ), "Zero infill thickness should return 0.0 kN/m²"

    def test_negative_thickness_returns_zero(self) -> None:
        expected_weight = 0.0
        assert (
            SuperficialLoads.get_infill_weight("Construction debris, rubble", -5.0)
            == expected_weight
        ), "Negative infill thickness should return 0.0 kN/m²"


class TestGetCeilingWeight:
    """Tests for the ceiling weight in kN/m²."""

    def test_drywall_ceiling(self) -> None:
        expected_weight = 0.25  # kN/m²
        assert (
            SuperficialLoads.get_ceiling_weight(
                "Drywall ceiling, includes support structure"
            )
            == expected_weight
        ), "Drywall ceiling should weigh 0.25 kN/m²"

    def test_mineral_fiber_ceiling(self) -> None:
        expected_weight = 0.10  # kN/m²
        assert (
            SuperficialLoads.get_ceiling_weight(
                "Mineral fiber ceiling, includes support structure"
            )
            == expected_weight
        ), "Mineral fiber ceiling should weigh 0.10 kN/m²"

    def test_empty_description_returns_zero(self) -> None:
        expected_weight = 0.0
        assert SuperficialLoads.get_ceiling_weight("") == expected_weight, (
            "An empty ceiling description should return 0.0 kN/m²"
        )


class TestGetTopFinishWeight:
    """Tests for the top finish weight in kN/m²."""

    def test_residential_floor_5cm(self) -> None:
        expected_weight = 1.0  # kN/m² (20 kN/m³ * 0.05 m)
        assert (
            SuperficialLoads.get_top_finish_weight(RESIDENTIAL_FLOOR, 5.0)
            == expected_weight
        ), "Residential floor finish at 5 cm should give 1.0 kN/m²"

    def test_residential_floor_7cm(self) -> None:
        expected_weight = 1.4  # kN/m² (20 kN/m³ * 0.07 m)
        assert_approx(
            SuperficialLoads.get_top_finish_weight(RESIDENTIAL_FLOOR, 7.0),
            expected_weight,
            "Residential floor finish at 7 cm should give 1.4 kN/m²",
        )

    def test_empty_description_returns_zero(self) -> None:
        expected_weight = 0.0
        assert SuperficialLoads.get_top_finish_weight("", 5.0) == expected_weight, (
            "An empty top finish description should return 0.0 kN/m²"
        )

    def test_zero_thickness_returns_zero(self) -> None:
        expected_weight = 0.0
        assert (
            SuperficialLoads.get_top_finish_weight(RESIDENTIAL_FLOOR, 0.0)
            == expected_weight
        ), "Zero top finish thickness should return 0.0 kN/m²"

    def test_negative_thickness_returns_zero(self) -> None:
        expected_weight = 0.0
        assert (
            SuperficialLoads.get_top_finish_weight(RESIDENTIAL_FLOOR, -1.0)
            == expected_weight
        ), "Negative top finish thickness should return 0.0 kN/m²"


class TestGetVariableUsageLoad:
    """Tests for the variable usage load lookup, keyed by building category.

    Each test overrides ``APP_CONFIG.building_category`` via monkeypatch before
    calling, since the production lookup reads the configured category.
    """

    def test_residential_bedrooms(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setattr(APP_CONFIG, "building_category", "Residential buildings")
        expected_load = 1.5  # kN/m²
        assert (
            SuperficialLoads.get_variable_usage_load("Bedrooms") == expected_load
        ), "Residential bedrooms should have a 1.5 kN/m² variable load"

    def test_residential_sports_courts(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setattr(APP_CONFIG, "building_category", "Residential buildings")
        expected_load = 5.0  # kN/m²
        assert (
            SuperficialLoads.get_variable_usage_load("Sports courts") == expected_load
        ), "Residential sports courts should have a 5.0 kN/m² variable load"

    def test_residential_service_area(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setattr(APP_CONFIG, "building_category", "Residential buildings")
        expected_load = 2.0  # kN/m²
        assert (
            SuperficialLoads.get_variable_usage_load(
                "Pantry, service area, and laundry"
            )
            == expected_load
        ), "Residential service area should have a 2.0 kN/m² variable load"

    def test_commercial_general_rooms(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setattr(
            APP_CONFIG,
            "building_category",
            "Commercial, corporate, and office buildings",
        )
        expected_load = 2.5  # kN/m²
        assert (
            SuperficialLoads.get_variable_usage_load(
                "General use rooms and bathrooms"
            )
            == expected_load
        ), "Commercial general rooms should have a 2.5 kN/m² variable load"
