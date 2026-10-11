"""Tests for src/loading/combination_factors.py."""

import pytest

from src.config import APP_CONFIG
from src.config_options import OccupancyCategory
from src.loading.combination_factors import almost_permanent_reduction_factor
from tests.helpers import assert_approx


def _set_category(monkeypatch: pytest.MonkeyPatch, category: OccupancyCategory) -> None:
    """Set the configured building category for one test"""
    monkeypatch.setattr(APP_CONFIG, "building_category", category)


class TestCategoryDefault:
    """psi_2 follows the configured building category when no local overrides it."""

    @pytest.mark.parametrize(
        "category, expected",
        [
            (OccupancyCategory.RESIDENTIAL, 0.3),
            (OccupancyCategory.HOTELS, 0.3),
            (OccupancyCategory.COMMERCIAL, 0.4),
            (OccupancyCategory.SCHOOLS, 0.4),
            (OccupancyCategory.LIBRARIES, 0.6),
            (OccupancyCategory.INDUSTRIAL, 0.6),
            (OccupancyCategory.GENERAL_WAREHOUSES, 0.6),
            (OccupancyCategory.GOODS_ACCUMULATION, 0.6),
            (OccupancyCategory.ROOFS, 0.6),
        ],
    )
    def test_category_factor(
        self,
        monkeypatch: pytest.MonkeyPatch,
        category: OccupancyCategory,
        expected: float,
    ) -> None:
        _set_category(monkeypatch, category)
        assert_approx(
            almost_permanent_reduction_factor(),
            expected,
            f"psi_2 for {category.value} should be {expected}",
        )

    def test_regular_local_keeps_category_factor(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        _set_category(monkeypatch, OccupancyCategory.COMMERCIAL)
        assert_approx(
            almost_permanent_reduction_factor("General use rooms and bathrooms"),
            0.4,
            "an ordinary office room should keep the commercial psi_2",
        )

    def test_unknown_local_keeps_category_factor(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        _set_category(monkeypatch, OccupancyCategory.RESIDENTIAL)
        assert_approx(
            almost_permanent_reduction_factor("Not a Table 10 local"),
            0.3,
            "an unknown local should fall back to the category psi_2",
        )


class TestLocalOverride:
    """Storage and archive locals use psi_2 = 0.6 in any building."""

    def test_storage_room_in_residential_building(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        _set_category(monkeypatch, OccupancyCategory.RESIDENTIAL)
        assert_approx(
            almost_permanent_reduction_factor("Storage rooms"),
            0.6,
            "a storage room should override the residential psi_2",
        )

    def test_archive_in_commercial_building(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        _set_category(monkeypatch, OccupancyCategory.COMMERCIAL)
        assert_approx(
            almost_permanent_reduction_factor("Sliding archive regions"),
            0.6,
            "an archive should override the commercial psi_2",
        )

    def test_override_needs_exact_description(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        _set_category(monkeypatch, OccupancyCategory.RESIDENTIAL)
        assert_approx(
            almost_permanent_reduction_factor("Storage"),
            0.3,
            "a partial local name must not trigger the override",
        )
