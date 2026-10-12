"""Read bar layers and stirrups from the engine's reinforcement objects."""

from collections import Counter
from typing import cast

from pavement_ui.core.results.reinforcement import BarGroup, BarLayer, StirrupSpec
from src.reinforcement.layer import Layer
from src.reinforcement.reinforcement import Reinforcement
from src.reinforcement.stirrups import Stirrups

_MM_PER_CM = 10.0


def _groups(layer: Layer) -> tuple[BarGroup, ...]:
    """Count bars per diameter, largest first (the engine repeats one Rebar object)."""
    counter = Counter(bar.diameter_mm for bar in layer.bars)
    return tuple(BarGroup(n, d) for d, n in sorted(counter.items(), reverse=True))


def read_layers(reinforcement: Reinforcement) -> tuple[BarLayer, ...]:
    """Return the non-empty chosen layers, numbered from 1 at the reinforced face

    Each layer's height is the engine's ``y_centroid_position``, measured from
    the bottom face of the section.
    """
    return tuple(
        BarLayer(layer.layer_index + 1, layer.y_centroid_position, _groups(layer))
        for layer in reinforcement.chosen_bars
        if layer.bars
    )


def read_stirrup(stirrups: Stirrups) -> StirrupSpec:
    """Return the chosen stirrups, with the diameter converted from cm to mm"""
    diameter_cm = cast(float, stirrups.diameter)
    spacing_cm = cast(float, stirrups.spacing)
    return StirrupSpec(diameter_cm * _MM_PER_CM, spacing_cm)
