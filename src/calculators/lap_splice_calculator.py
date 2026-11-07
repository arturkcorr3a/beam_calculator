from src.calculators.anchorage_calculator import AnchorageCalculator
from src.properties.steel import Steel

MAX_LAP_DIAMETER_MM = (
    32.0  # mm, larger bars cannot be lap spliced - NBR 6118 - Section 9.5.2
)
MIN_LAP_LENGTH = 20.0  # cm - NBR 6118 - Sections 9.5.2.2.1 and 9.5.2.3
MIN_LAP_DIAMETERS = 15  # bar diameters - NBR 6118 - Sections 9.5.2.2.1 and 9.5.2.3

# Table 9.4: upper limit of the share of bars spliced in one section → α_0t
_ALPHA_0T_TABLE: tuple[tuple[float, float], ...] = (
    (0.20, 1.2),
    (0.25, 1.4),
    (1 / 3, 1.6),
    (0.50, 1.8),
)
_ALPHA_0T_ABOVE_HALF = 2.0
_SHARE_TOLERANCE = 1e-9
_MM_PER_CM = 10.0


def alpha_0t(share: float) -> float:
    """Return the lap coefficient α_0t for the share of bars spliced in one section

    The share is matched to the first column of Table 9.4 that is not below it, so values between columns take the next, larger coefficient.

    Args:
        share: Bars spliced in the same section over all the bars there, from 0 to 1.

    References:
        ABNT NBR 6118:2026 — Section 9.5.2.2.1, Table 9.4
    """
    for limit, coefficient in _ALPHA_0T_TABLE:
        if share <= limit + _SHARE_TOLERANCE:
            return coefficient
    return _ALPHA_0T_ABOVE_HALF


def tension_lap_length(
    diameter_mm: float,
    steel: Steel,
    good_adherence: bool,
    area_ratio: float,
    share: float,
) -> float:
    """Return the lap length l_0t of tensioned bars in contact (cm)

    The necessary anchorage length of a straight bar, times α_0t, and at least the greatest of 0.3 α_0t l_b, 15φ and 20 cm. The bars are taken as in contact, so no clear distance is added.

    Args:
        diameter_mm: Diameter φ of the spliced bars, the smaller one when they differ (mm).
        good_adherence: Whether the splice sits in a good bond zone.
        area_ratio: Required over provided steel area, A_s,calc / A_s,ef.
        share: Bars spliced in the same section over all the bars there, from 0 to 1.

    References:
        ABNT NBR 6118:2026 — Sections 9.4.2.5 and 9.5.2.2
    """
    basic_length = _basic_length(diameter_mm, steel, good_adherence)  # cm
    coefficient = alpha_0t(share)
    return max(
        coefficient * _necessary_length(basic_length, diameter_mm, area_ratio),
        0.3 * coefficient * basic_length,
        _diameter_minimum(diameter_mm),
        MIN_LAP_LENGTH,
    )


def compression_lap_length(
    diameter_mm: float, steel: Steel, good_adherence: bool, area_ratio: float
) -> float:
    """Return the lap length l_0c of compressed bars (cm)

    The necessary anchorage length of a straight bar, and at least the greatest of 0.6 l_b, 15φ and 20 cm.

    Args:
        diameter_mm: Diameter φ of the spliced bars, the smaller one when they differ (mm).
        good_adherence: Whether the splice sits in a good bond zone.
        area_ratio: Required over provided steel area, A_s,calc / A_s,ef.

    References:
        ABNT NBR 6118:2026 — Sections 9.4.2.5 and 9.5.2.3
    """
    basic_length = _basic_length(diameter_mm, steel, good_adherence)  # cm
    return max(
        _necessary_length(basic_length, diameter_mm, area_ratio),
        construction_lap_length(diameter_mm, steel, good_adherence),
    )


def construction_lap_length(
    diameter_mm: float, steel: Steel, good_adherence: bool
) -> float:
    """Return the lap length of construction bars, which carry no calculated force (cm)

    The minimum lap of compressed bars, l_0c,min: the greatest of 0.6 l_b, 15φ and 20 cm.

    Args:
        diameter_mm: Diameter φ of the construction bars (mm).
        good_adherence: Whether the splice sits in a good bond zone.

    References:
        ABNT NBR 6118:2026 — Section 9.5.2.3
    """
    basic_length = _basic_length(diameter_mm, steel, good_adherence)  # cm
    return max(0.6 * basic_length, _diameter_minimum(diameter_mm), MIN_LAP_LENGTH)


def _basic_length(diameter_mm: float, steel: Steel, good_adherence: bool) -> float:
    """Return the basic anchorage length l_b of a bar (cm)"""
    bond_strength = AnchorageCalculator.design_bond_strength_for(
        diameter_mm, steel, good_adherence
    )
    return AnchorageCalculator.basic_anchorage_length_for(
        diameter_mm, steel, bond_strength
    )


def _necessary_length(
    basic_length: float, diameter_mm: float, area_ratio: float
) -> float:
    """Return the necessary anchorage length l_b,nec of a straight bar (α = 1), at least l_b,min (cm)"""
    return max(
        area_ratio * basic_length,
        AnchorageCalculator.min_anchorage_length_for(basic_length, diameter_mm),
    )


def _diameter_minimum(diameter_mm: float) -> float:
    """Return 15 bar diameters (cm)"""
    return MIN_LAP_DIAMETERS * diameter_mm / _MM_PER_CM
