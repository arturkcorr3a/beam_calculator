"""Unit tests for the AppConfig dataclass and its defaults."""

import pytest

import src.logger as logger_module
from src.config import APP_CONFIG, AppConfig
from src.config_options import Aggregate, ExposureClass, OccupancyCategory
from src.logger import LogLevel, LogOutput
from src.properties.concrete import Concrete
from src.properties.steel import Steel
from tests.helpers import assert_approx

# TODO add test checking if all the config entries are present in serialization


@pytest.fixture
def config() -> AppConfig:
    """Fresh AppConfig with all default values."""
    return AppConfig()


class TestAppConfigDefaults:
    """Tests pinning the default field values that the persistency layer mirrors."""

    def test_aggregate(self, config: AppConfig) -> None:
        assert config.aggregate is Aggregate.GRANITE, (
            "The default aggregate should be granite"
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
        assert config.pavement_concrete is Concrete.C30, (
            "The default pavement concrete should be C30"
        )

    def test_pavement_steel(self, config: AppConfig) -> None:
        assert config.pavement_steel is Steel.CA50, (
            "The default pavement steel should be CA50"
        )

    def test_building_category(self, config: AppConfig) -> None:
        assert config.building_category is OccupancyCategory.RESIDENTIAL, (
            "The default building category should be residential"
        )

    def test_exposure_class(self, config: AppConfig) -> None:
        assert config.exposure_class is ExposureClass.MODERATE, (
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
        assert config.log_level is LogLevel.PROPERTY, (
            "The default log level should be PROPERTY"
        )

    def test_log_output(self, config: AppConfig) -> None:
        assert config.log_output is LogOutput.BOTH, (
            "The default log output should be BOTH"
        )


class TestAppConfigSlots:
    """Tests that AppConfig rejects attributes it does not declare."""

    def test_unknown_attribute_raises(self, config: AppConfig) -> None:
        with pytest.raises(AttributeError):
            setattr(config, "default_concrete", Concrete.C25)  # noqa: B010


class TestLoggerConfiguration:
    """Tests that importing src.config applies APP_CONFIG to the module logger."""

    def test_logger_level_matches_app_config(self) -> None:
        assert logger_module._logger._level is APP_CONFIG.log_level, (  # pyright: ignore[reportPrivateUsage]
            "The module logger level should match APP_CONFIG.log_level"
        )

    def test_logger_output_matches_app_config(self) -> None:
        assert logger_module._logger._output is APP_CONFIG.log_output, (  # pyright: ignore[reportPrivateUsage]
            "The module logger output should match APP_CONFIG.log_output"
        )


class TestIsConcreteGreaterThanMinimum:
    """Tests for the minimum-concrete-grade check across every exposure class."""

    @pytest.mark.parametrize(
        ("exposure_class", "fck", "expected"),
        [
            # Class 1 — minimum 20 MPa
            (ExposureClass.WEAK, 21, True),
            (ExposureClass.WEAK, 20, False),
            (ExposureClass.WEAK, 19, False),
            # Class 2 — minimum 25 MPa
            (ExposureClass.MODERATE, 26, True),
            (ExposureClass.MODERATE, 25, False),
            (ExposureClass.MODERATE, 24, False),
            # Class 3 — minimum 30 MPa
            (ExposureClass.SEVERE, 31, True),
            (ExposureClass.SEVERE, 30, False),
            (ExposureClass.SEVERE, 29, False),
            # Class 4 — minimum 40 MPa
            (ExposureClass.VERY_SEVERE, 41, True),
            (ExposureClass.VERY_SEVERE, 40, False),
            (ExposureClass.VERY_SEVERE, 39, False),
        ],
    )
    def test_threshold_per_exposure_class(
        self,
        config: AppConfig,
        exposure_class: ExposureClass,
        fck: float,
        expected: bool,
    ) -> None:
        config.exposure_class = exposure_class
        assert config.is_concrete_greater_than_minimum(fck) is expected, (
            f"For exposure class {exposure_class}, fck {fck} MPa should return {expected} "
            "(check is a strict greater-than against the class minimum)"
        )
