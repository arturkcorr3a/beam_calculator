from __future__ import annotations

from dataclasses import dataclass


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

    # PAPER find ref for standard ceiling height for residential buildings
    ceiling_height: float = 2.5  # m


APP_CONFIG = AppConfig()
