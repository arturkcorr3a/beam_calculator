from collections.abc import Iterable
from dataclasses import dataclass

from src.calculators.lap_splice_calculator import (
    compression_lap_length,
    tension_lap_length,
)
from src.detailing.detailed_bar import DetailedBar

SAME_SECTION_RATIO = 0.2  # splices closer than this share of the lap are in one section - NBR 6118 - Section 9.5.2.1
MULTI_LAYER_MAX_SHARE = 0.5  # tensioned bars spliced in one section with more than one layer - NBR 6118 - Table 9.3


@dataclass(frozen=True, kw_only=True)
class LapSplice:
    """A lap splice between two bar runs on the same face and layer

    Attributes:
        layer_index: Layer of the spliced bars, 0 being the closest to the face.
        start: Left end of the lap: the right-hand bars' start (cm).
        end: Right end of the lap: the left-hand bars' end (cm).
        quantity: Number of bar pairs spliced.
        diameter_mm: Diameter the lap was sized with, the smaller of the two (mm).
    """

    is_bottom: bool
    layer_index: int
    start: float  # cm
    end: float  # cm
    quantity: int
    diameter_mm: float

    @property
    def length(self) -> float:
        """Return the lap length (cm)"""
        return self.end - self.start


def spliced_near(
    lap_splices: Iterable[LapSplice], is_bottom: bool, start: float, end: float
) -> int:
    """Count the bars of laps on a face that share a section with a lap in [start, end] (cm)

    Two laps share a section when they overlap or their nearest ends are closer than 20 % of the lap length.

    References:
        ABNT NBR 6118:2026 — Section 9.5.2.1
    """
    margin = SAME_SECTION_RATIO * (end - start)  # cm
    return sum(
        lap.quantity
        for lap in lap_splices
        if lap.is_bottom == is_bottom
        and lap.start < end + margin
        and lap.end > start - margin
    )


def section_share(
    bars: Iterable[DetailedBar],
    lap_splices: Iterable[LapSplice],
    *,
    is_bottom: bool,
    center: float,
    reach: float,
    quantity: int,
    paired_quantity: int = 0,
) -> tuple[float, int]:
    """Return the share of a face's bars spliced in the section of a new lap, and the layers there

    The bars crossing the section are counted with each lapped pair once: the pairs of the laps already there, and the new lap's own pair when both of its bar runs are already in ``bars``. The spliced bars are the new lap's and those of the laps sharing its section (``spliced_near``).

    Args:
        center: Center of the new lap (cm).
        reach: Half of the longest the new lap can be (cm).
        quantity: Bars spliced by the new lap.
        paired_quantity: Bars of the new lap counted on both of its sides in ``bars``, counted once.

    Returns:
        The share, from 0 to 1, and the number of layers with bars in the section.

    References:
        ABNT NBR 6118:2026 — Section 9.5.2.1, Tables 9.3 and 9.4
    """
    laps = [lap for lap in lap_splices if lap.is_bottom == is_bottom]
    crossing = [
        bar
        for bar in bars
        if bar.is_bottom == is_bottom and bar.start <= center <= bar.end
    ]
    count = (
        sum(bar.quantity for bar in crossing)
        - sum(lap.quantity for lap in laps if lap.start <= center <= lap.end)
        - paired_quantity
    )
    spliced = quantity + spliced_near(laps, is_bottom, center - reach, center + reach)
    layers = len({bar.layer_index for bar in crossing})
    return min(spliced / max(count, 1), 1.0), layers


def exceeds_spliced_share(share: float, layers: int, is_tensioned: bool) -> bool:
    """Whether a lap would splice more tensioned bars in one section than Table 9.3 allows

    High-bond bars may all be spliced in one section when they sit in one layer, and up to half of them with more than one layer. Compressed bars may all be spliced.

    References:
        ABNT NBR 6118:2026 — Section 9.5.2.1, Table 9.3
    """
    return is_tensioned and layers > 1 and share > MULTI_LAYER_MAX_SHARE


def splice_length(a: DetailedBar, b: DetailedBar, share: float) -> float:
    """Return the lap length of a splice between two bar runs (cm), sized with the smaller diameter

    Tension lap unless both runs are compressed; compression lap when both are. The splice is in a good bond zone only if both runs are, and the larger area ratio is used. A bar split in two is spliced with itself.

    Args:
        share: Bars spliced in the same section over all the bars there.

    References:
        ABNT NBR 6118:2026 — Sections 9.5.2.1, 9.5.2.2 and 9.5.2.3
    """
    diameter_mm = min(a.diameter_mm, b.diameter_mm)
    good_adherence = a.good_adherence and b.good_adherence
    area_ratio = max(a.area_ratio, b.area_ratio)
    if not (a.is_tensioned or b.is_tensioned):
        return compression_lap_length(diameter_mm, a.steel, good_adherence, area_ratio)
    return tension_lap_length(diameter_mm, a.steel, good_adherence, area_ratio, share)
