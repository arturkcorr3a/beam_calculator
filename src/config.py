from __future__ import annotations

from dataclasses import dataclass
from math import ceil

from src.config_options import Aggregate, ExposureClass, OccupancyCategory
from src.logger import LogLevel, LogOutput, configure_logger
from src.properties.concrete import Concrete
from src.properties.steel import Steel

# NOTE: When adding, removing, or renaming a field here, update ConfigDict in
# src/persistency/schema.py, config_to_dict in serialization.py, and
# config_from_dict in deserialization.py in lockstep.

AGGREGATE_COVER_FACTOR = 1.2  # ABNT NBR 6118:2026 - Section 7.4.7.6
COVER_ROUNDING_STEP = 0.5  # cm
_ROUNDING_TOLERANCE = 1e-9  # absorbs float drift on exact multiples of the step


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

    def is_concrete_greater_than_minimum(self, fck: float) -> bool:
        """Check whether fck strictly exceeds the minimum for the exposure class

        Used to grant the nominal cover reduction allowed when the concrete is
        stronger than the minimum required.

        Args:
            fck: Concrete characteristic compressive strength (MPa).

        References:
            ABNT NBR 6118:2026 — Section 7.4.2, Table 7.1
            ABNT NBR 6118:2026 — Section 7.4.7.6
        """
        return fck > self.exposure_class.minimum_fck

    def minimum_nominal_cover_for_aggregate(self) -> float:
        """Get the smallest nominal cover the coarse aggregate allows

        The maximum aggregate size cannot exceed the nominal cover by more than 20 %. The resulting cover is rounded up to the next 0.5 cm step, the same step used by Table 7.2.

        Returns:
            Minimum nominal cover (cm).

        References:
            ABNT NBR 6118:2026 — Section 7.4.7.6
        """
        steps = self.max_aggregate_size / AGGREGATE_COVER_FACTOR / COVER_ROUNDING_STEP
        return ceil(steps - _ROUNDING_TOLERANCE) * COVER_ROUNDING_STEP

    def validate_concrete_class(self) -> None:
        """Ensure the pavement concrete meets the minimum for the exposure class

        Raises:
            ValueError: If the pavement concrete fck is below the minimum
                required for the configured exposure class.

        References:
            ABNT NBR 6118:2026 — Section 7.4.2, Table 7.1
        """
        minimum_fck = self.exposure_class.minimum_fck
        if self.pavement_concrete.value < minimum_fck:
            raise ValueError(
                f"Concrete {self.pavement_concrete.name} is below the minimum "
                f"C{minimum_fck} required for exposure class "
                f"{self.exposure_class.value}."
            )


APP_CONFIG = AppConfig()
configure_logger(APP_CONFIG.log_level, APP_CONFIG.log_output)
