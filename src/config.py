from __future__ import annotations

from dataclasses import dataclass

# NOTE: When adding, removing, or renaming a field here, update ConfigDict in
# src/persistency/schema.py, config_to_dict in serialization.py, and
# config_from_dict in deserialization.py in lockstep.


@dataclass
class AppConfig:
    # Default material grades — map to Steel/Concrete enum names, resolved at runtime
    steel: str = "CA50"
    default_concrete: str = "C30"

    # Reinforcement layout — user-facing construction preferences
    max_aggregate_size: float = 2.5  # cm
    max_bar_types: int = 3
    max_layers: int = 3

    # Pavement project-level material defaults (apply to all beams and slabs)
    pavement_concrete: str = "C30"
    pavement_steel: str = "CA50"

    building_category: str = "Residential buildings"

    ceiling_height: float = 2.5  # m, reference: ABNT NBR 15575-1, section 16.1

    # Logging configuration — debug only, not persisted to saved.yaml
    # log_level options: PROPERTY, OPERATION, ITERATION, ELEMENT, INTERACTION, GENERAL, DISABLED
    log_level: str = "PROPERTY"
    # log_output options: console, file, both
    log_output: str = "console"

    # TODO maybe make it variable based on default configs and maybe turn into a static function?
    @property
    def nominal_covering(self) -> float:
        """
        Returns the nominal covering (cm) for a beam with class 2 exposure, with 10 mm execution tolerance, based on ABNT NBR 6118 - Section 7.4.
        """
        return 3.0


APP_CONFIG = AppConfig()
