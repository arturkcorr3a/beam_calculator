"""Map the core's ConfigValues to and from the engine's global APP_CONFIG.

Keep in sync with ``src/config.py``'s ``AppConfig`` (see AGENTS.md).
"""

from dataclasses import fields

from pavement_ui.core.engine.keys import from_key, to_key
from pavement_ui.core.model.settings import ConfigValues
from src.config import APP_CONFIG, AppConfig
from src.config_options import Aggregate, ExposureClass, OccupancyCategory
from src.properties.concrete import Concrete
from src.properties.steel import Steel

type ConfigSnapshot = dict[str, object]


def apply(config: ConfigValues) -> None:
    """Write the project settings to APP_CONFIG (log settings are untouched)"""
    APP_CONFIG.pavement_concrete = from_key(Concrete, config.concrete_key)
    APP_CONFIG.pavement_steel = from_key(Steel, config.steel_key)
    APP_CONFIG.aggregate = from_key(Aggregate, config.aggregate_key)
    APP_CONFIG.max_aggregate_size = config.max_aggregate_size_cm
    APP_CONFIG.max_bar_types = config.max_bar_types
    APP_CONFIG.max_layers = config.max_layers
    APP_CONFIG.exposure_class = from_key(ExposureClass, config.exposure_key)
    APP_CONFIG.building_category = from_key(
        OccupancyCategory, config.building_category_key
    )
    APP_CONFIG.ceiling_height = config.ceiling_height_m


def read() -> ConfigValues:
    """Return the project settings currently in APP_CONFIG"""
    return ConfigValues(
        concrete_key=to_key(APP_CONFIG.pavement_concrete),
        steel_key=to_key(APP_CONFIG.pavement_steel),
        aggregate_key=to_key(APP_CONFIG.aggregate),
        max_aggregate_size_cm=APP_CONFIG.max_aggregate_size,
        max_bar_types=APP_CONFIG.max_bar_types,
        max_layers=APP_CONFIG.max_layers,
        exposure_key=to_key(APP_CONFIG.exposure_class),
        building_category_key=to_key(APP_CONFIG.building_category),
        ceiling_height_m=APP_CONFIG.ceiling_height,
    )


def snapshot() -> ConfigSnapshot:
    """Capture every AppConfig field, to undo an operation that changes it"""
    return {f.name: getattr(APP_CONFIG, f.name) for f in fields(AppConfig)}


def restore(saved: ConfigSnapshot) -> None:
    """Put back the fields captured by ``snapshot``"""
    for name, value in saved.items():
        setattr(APP_CONFIG, name, value)
