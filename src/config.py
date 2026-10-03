from __future__ import annotations

from dataclasses import dataclass

# NOTE: When adding, removing, or renaming a field here, update ConfigDict in
# src/persistency/schema.py, config_to_dict in serialization.py, and
# config_from_dict in deserialization.py in lockstep.


# TODO use more robust typing, with literals and enums
@dataclass
class AppConfig:
    # options: granite, basalt, diabase, limestone, sandstone
    aggregate: str = "granite"
    # Reinforcement layout — user-facing construction preferences
    max_aggregate_size: float = 2.5  # cm
    max_bar_types: int = 3
    max_layers: int = 3

    # Pavement project-level material defaults (apply to all beams and slabs)
    pavement_concrete: str = "C30"
    pavement_steel: str = "CA50"

    building_category: str = "Residential buildings"

    # options: 1 (weak), 2 (moderate), 3 (severe), 4 (very severe)
    exposure_class: int = 2  # ABNT NBR 6118 - Section 6.4 - Table 6.1

    ceiling_height: float = 2.5  # m, reference: ABNT NBR 15575-1, section 16.1

    # Logging configuration — debug only, not persisted to saved.yaml
    # log_level options: PROPERTY, OPERATION, ITERATION, ELEMENT, INTERACTION, GENERAL, DISABLED
    log_level: str = "PROPERTY"
    # log_output options: console, file, both
    log_output: str = "both"

    # TODO should validate lower than the minimum concrete grade for the exposure class
    def is_concrete_greater_than_minimum(self, fck: float) -> bool:
        """Get the minimum concrete grade for the configured exposure class, based on ABNT NBR 6118 - Section 7.4.2 - Table 7.1."""
        exposure_class = self.exposure_class
        match exposure_class:
            case 1:
                return fck > 20
            case 2:
                return fck > 25
            case 3:
                return fck > 30
            case 4:
                return fck > 40
            case _:
                raise ValueError(
                    f"Invalid exposure class: {exposure_class}. Must be between 1 and 4."
                )


APP_CONFIG = AppConfig()
