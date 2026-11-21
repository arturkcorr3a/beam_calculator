"""Split the bending moment of a section among its bar layers, for staggering the bars."""

from collections.abc import Sequence

from src.errors import EnginePreconditionError

type MomentBand = tuple[float, float]  # kN.m, (lower, upper)


def layer_moment_bands(
    layer_areas: Sequence[float], section_moment: float
) -> list[MomentBand]:
    """Split the section moment into one band per layer, proportional to the layers' areas

    The first layer (next to the tensioned face) takes the band from zero moment up, and the innermost layer takes the band that ends at the section moment. Each band spans the share of the moment equal to the layer's share of the total area.

    Args:
        layer_areas: Steel area of each non-empty layer, from the tensioned face inwards (cm²).
        section_moment: Bending moment of the section (kN.m), signed; the bands keep its sign.

    Returns:
        The (lower, upper) moments of each layer's band (kN.m), in the same order. The first lower is exactly zero and the last upper is exactly the section moment.

    Raises:
        EnginePreconditionError: If there is no layer or the total area is not positive.

    References:
        ABNT NBR 6118:2026 — Section 18.3.2.3.1 (Figure 18.3)
        Carvalho e Figueiredo Filho (2014) — Chapter 5, staggering of the longitudinal bars.
    """
    total_area = sum(layer_areas)  # cm²
    if not layer_areas or total_area <= 0:
        raise EnginePreconditionError("The layers must have a positive total area.")
    bands: list[MomentBand] = []
    lower = 0.0  # kN.m
    cumulative_area = 0.0  # cm²
    for index, area in enumerate(layer_areas):
        cumulative_area += area
        is_last = index == len(layer_areas) - 1
        upper = (
            section_moment if is_last else section_moment * cumulative_area / total_area
        )
        bands.append((lower, upper))
        lower = upper
    return bands


def nearest_distance(
    center: float,
    positions: Sequence[float],
    left: bool,
    limit: float | None = None,
) -> float | None:
    """Return the distance from a section to the nearest position on one side of it

    Args:
        center: Position of the section along the beam (cm).
        positions: Candidate positions along the beam (cm).
        left: Whether to look to the left of the section; otherwise to the right.
        limit: Largest distance accepted (cm); positions farther away are ignored. None accepts any distance.

    Returns:
        Distance in cm, or None if no position lies on that side within the limit.
    """
    distances = [
        center - position if left else position - center for position in positions
    ]
    on_side = [
        distance
        for distance in distances
        if distance > 0 and (limit is None or distance <= limit)
    ]
    return min(on_side) if on_side else None
