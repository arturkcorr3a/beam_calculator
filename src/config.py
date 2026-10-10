from __future__ import annotations

from dataclasses import dataclass
from typing import assert_never

from src.config_options import Aggregate, ExposureClass, OccupancyCategory
from src.logger import LogLevel, LogOutput, configure_logger
from src.properties.concrete import Concrete
from src.properties.steel import Steel

# NOTE: When adding, removing, or renaming a field here, update ConfigDict in
# src/persistency/schema.py, config_to_dict in serialization.py, and
# config_from_dict in deserialization.py in lockstep.


@dataclass(slots=True)
class AppConfig:
    aggregate: Aggregate = Aggregate.GRANITE
    # Reinforcement layout — user-facing construction preferences
    max_aggregate_size: float = 2.5  # cm
    max_bar_types: int = 3
    max_layers: int = 3

    # Pavement project-level material defaults (apply to all beams and slabs)
    pavement_concrete: Concrete = Concrete.C30
    pavement_steel: Steel = Steel.CA50

    building_category: OccupancyCategory = OccupancyCategory.RESIDENTIAL

    # ABNT NBR 6118 - Section 6.4 - Table 6.1
    exposure_class: ExposureClass = ExposureClass.MODERATE

    ceiling_height: float = 2.5  # m, reference: ABNT NBR 15575-1, section 16.1

    # Logging configuration — debug only, not persisted to saved.yaml
    log_level: LogLevel = LogLevel.PROPERTY
    log_output: LogOutput = LogOutput.BOTH

    # TODO should validate lower than the minimum concrete grade for the exposure class
    def is_concrete_greater_than_minimum(self, fck: float) -> bool:
        """Get the minimum concrete grade for the configured exposure class, based on ABNT NBR 6118 - Section 7.4.2 - Table 7.1."""
        exposure_class = self.exposure_class
        match exposure_class:
            case ExposureClass.WEAK:
                return fck > 20
            case ExposureClass.MODERATE:
                return fck > 25
            case ExposureClass.SEVERE:
                return fck > 30
            case ExposureClass.VERY_SEVERE:
                return fck > 40
            case _:
                assert_never(exposure_class)


APP_CONFIG = AppConfig()
configure_logger(APP_CONFIG.log_level, APP_CONFIG.log_output)
