from __future__ import annotations

from dataclasses import dataclass

# NOTE: When adding, removing, or renaming a field here, update ConfigDict in
# src/persistency/schema.py, config_to_dict in serialization.py, and
# config_from_dict in deserialization.py in lockstep.

# TODO use more robust typing, with literals and enums
@dataclass
class AppConfig:
    # Default material grades — map to Steel/Concrete enum names, resolved at runtime
    steel: str = "CA50"
    default_concrete: str = "C30"

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
    log_output: str = "console"


APP_CONFIG = AppConfig()
