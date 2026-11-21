"""General project settings, as edited in the configuration dialog.

Keep in sync with ``src/config.py``'s ``AppConfig`` (see AGENTS.md); defaults
equal ``AppConfig()``.
"""

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class ConfigValues:
    """Project settings saved with the pavement file

    Attributes:
        concrete_key: Concrete class key (e.g. "C30").
        steel_key: Steel key (e.g. "CA50").
        aggregate_key: Aggregate key (e.g. "GRANITE").
        max_aggregate_size_cm: Maximum aggregate size (cm), > 0.
        max_bar_types: Maximum number of different bar diameters per reinforcement, ≥ 1.
        max_layers: Maximum number of bar layers, ≥ 1.
        exposure_key: Environmental aggressiveness class key (e.g. "MODERATE").
        building_category_key: NBR 6120 Table 10 category key (e.g. "RESIDENTIAL").
        ceiling_height_m: Ceiling height (m), > 0.
    """

    concrete_key: str = "C30"
    steel_key: str = "CA50"
    aggregate_key: str = "GRANITE"
    max_aggregate_size_cm: float = 2.5
    max_bar_types: int = 3
    max_layers: int = 3
    exposure_key: str = "MODERATE"
    building_category_key: str = "RESIDENTIAL"
    ceiling_height_m: float = 2.5


@dataclass(frozen=True, slots=True)
class LogValues:
    """Calculation memorial settings — never saved to the file [Manual]

    Attributes:
        level_key: Log level key (e.g. "GENERAL").
    """

    level_key: str = "GENERAL"
