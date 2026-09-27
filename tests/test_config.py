"""Unit tests for the AppConfig dataclass and its defaults."""

import pytest

from src.config import AppConfig
from tests.helpers import assert_approx

# TODO add test checking if all the config entries are present in serialization


@pytest.fixture
def config() -> AppConfig:
    """Fresh AppConfig with all default values."""
    return AppConfig()


class TestAppConfigDefaults:
    """Tests pinning the default field values that the persistency layer mirrors."""

    def test_aggregate(self, config: AppConfig) -> None:
        assert config.aggregate == "granite", (
            "The default aggregate should be 'granite'"
        )

    def test_max_aggregate_size(self, config: AppConfig) -> None:
        expected_max_aggregate_size = 2.5  # cm
        assert_approx(
            config.max_aggregate_size,
            expected_max_aggregate_size,
            "The default max aggregate size should be 2.5 cm",
        )

    def test_max_bar_types(self, config: AppConfig) -> None:
        expected_max_bar_types = 3
        assert config.max_bar_types == expected_max_bar_types, (
            "The default max bar types should be 3"
        )

    def test_max_layers(self, config: AppConfig) -> None:
        expected_max_layers = 3
        assert config.max_layers == expected_max_layers, (
            "The default max layers should be 3"
        )

    def test_pavement_concrete(self, config: AppConfig) -> None:
        assert config.pavement_concrete == "C30", (
            "The default pavement concrete should be 'C30'"
        )

    def test_pavement_steel(self, config: AppConfig) -> None:
        assert config.pavement_steel == "CA50", (
            "The default pavement steel should be 'CA50'"
        )

    def test_building_category(self, config: AppConfig) -> None:
        assert config.building_category == "Residential buildings", (
            "The default building category should be 'Residential buildings'"
        )

    def test_exposure_class(self, config: AppConfig) -> None:
        expected_exposure_class = 2
        assert config.exposure_class == expected_exposure_class, (
            "The default exposure class should be 2 (moderate)"
        )

    def test_ceiling_height(self, config: AppConfig) -> None:
        expected_ceiling_height = 2.5  # m
        assert_approx(
            config.ceiling_height,
            expected_ceiling_height,
            "The default ceiling height should be 2.5 m",
        )

    def test_log_level(self, config: AppConfig) -> None:
        assert config.log_level == "PROPERTY", (
            "The default log level should be 'PROPERTY'"
        )

    def test_log_output(self, config: AppConfig) -> None:
        assert config.log_output == "both", "The default log output should be 'both'"


class TestIsConcreteGreaterThanMinimum:
    """Tests for the minimum-concrete-grade check across every exposure class."""

    @pytest.mark.parametrize(
        ("exposure_class", "fck", "expected"),
        [
            # Class 1 — minimum 20 MPa
            (1, 21, True),
            (1, 20, False),
            (1, 19, False),
            # Class 2 — minimum 25 MPa
            (2, 26, True),
            (2, 25, False),
            (2, 24, False),
            # Class 3 — minimum 30 MPa
            (3, 31, True),
            (3, 30, False),
            (3, 29, False),
            # Class 4 — minimum 40 MPa
            (4, 41, True),
            (4, 40, False),
            (4, 39, False),
        ],
    )
    def test_threshold_per_exposure_class(
        self,
        config: AppConfig,
        exposure_class: int,
        fck: float,
        expected: bool,
    ) -> None:
        config.exposure_class = exposure_class
        assert config.is_concrete_greater_than_minimum(fck) is expected, (
            f"For exposure class {exposure_class}, fck {fck} MPa should return {expected} "
            "(check is a strict greater-than against the class minimum)"
        )

    def test_invalid_exposure_class_raises(self, config: AppConfig) -> None:
        config.exposure_class = 5
        with pytest.raises(ValueError, match="Invalid exposure class"):
            _ = config.is_concrete_greater_than_minimum(30)
