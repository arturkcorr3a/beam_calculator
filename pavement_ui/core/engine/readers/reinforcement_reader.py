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


def read_layers(
    reinforcement: Reinforcement, face_offset_cm: float
) -> tuple[BarLayer, ...]:
    """Return the non-empty chosen layers, numbered from 1 at the reinforced face

    The engine's ``y_centroid_position`` is measured from the inner face of the
    stirrup, not from the section edge (bug M16), so it is shifted by
    face_offset_cm to get the height from the bottom face.

    Args:
        face_offset_cm: Cover plus stirrup diameter (cm), as used for d.
    """
    shift = face_offset_cm if reinforcement.is_bottom_reinforcement else -face_offset_cm
    return tuple(
        BarLayer(
            layer.layer_index + 1, layer.y_centroid_position + shift, _groups(layer)
        )
        for layer in reinforcement.chosen_bars
        if layer.bars
    )


def read_stirrup(stirrups: Stirrups) -> StirrupSpec:
    """Return the chosen stirrups, with the diameter converted from cm to mm"""
    diameter_cm = cast(float, stirrups.diameter)
    spacing_cm = cast(float, stirrups.spacing)
    return StirrupSpec(diameter_cm * _MM_PER_CM, spacing_cm)
