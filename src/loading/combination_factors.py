from src.config import APP_CONFIG
from src.config_options import OccupancyCategory
from src.logger import log_property

# PAPER confirm the ABNT NBR 8681:2025 table that lists psi_2 for building usage loads
# Predominance of fixed equipment or of high concentrations of people
PSI_2_DEFAULT = 0.4

_CATEGORY_PSI_2: dict[OccupancyCategory, float] = {
    # No predominance of long-standing fixed weights nor of crowds
    OccupancyCategory.RESIDENTIAL: 0.3,
    OccupancyCategory.HOTELS: 0.3,
    # Libraries, archives, deposits, workshops, garages and roofs
    OccupancyCategory.LIBRARIES: 0.6,
    OccupancyCategory.INDUSTRIAL: 0.6,
    OccupancyCategory.GENERAL_WAREHOUSES: 0.6,
    OccupancyCategory.GOODS_ACCUMULATION: 0.6,
    OccupancyCategory.ROOFS: 0.6,
}

# Locals (ABNT NBR 6120:2019 Table 10 descriptions) whose psi_2 overrides the category's
_LOCAL_PSI_2: dict[str, float] = {
    "Storage rooms": 0.6,
    "Sliding archive regions": 0.6,
}


def almost_permanent_reduction_factor(local: str | None = None) -> float:
    """Get the quasi-permanent reduction factor psi_2 for a local of the configured building

    The factor follows APP_CONFIG.building_category (0.3 for residential use, 0.4 for commercial or public access use, 0.6 for libraries, archives, deposits, workshops and roofs); a local that stores goods or archives overrides it with 0.6. The local must match its description exactly; an unknown or missing local falls back to the category's factor.

    Args:
        local: Usage local, as described in ABNT NBR 6120:2019 Table 10.

    Returns:
        The reduction factor psi_2 (dimensionless).

    References:
        ABNT NBR 6118:2026 — Table 11.2
        ABNT NBR 8681:2025
    """
    category = APP_CONFIG.building_category
    if local is not None and local in _LOCAL_PSI_2:
        psi_2 = _LOCAL_PSI_2[local]
    else:
        psi_2 = _CATEGORY_PSI_2.get(category, PSI_2_DEFAULT)
    log_property(f"psi_2 = {psi_2:.1f} ({category.value}; {local or 'no local'})")
    return psi_2
