"""pt-BR labels of the engine's option keys (docs/UI_SPEC.md §7.3).

A key without a label is shown as the key itself, so a new engine option never
breaks the interface.
"""

from collections.abc import Mapping
from enum import Enum, auto
from typing import Final

from pavement_ui.presentation.text.category_labels import CATEGORY_LABELS
from pavement_ui.presentation.text.masonry_labels import MASONRY_LABELS
from pavement_ui.presentation.text.usage_labels import USAGE_LABELS


class OptionKind(Enum):
    ALIGNMENT = auto()
    CONCRETE = auto()
    STEEL = auto()
    AGGREGATE = auto()
    EXPOSURE = auto()
    CATEGORY = auto()
    USAGE = auto()
    MASONRY = auto()
    LOG_LEVEL = auto()
    LOG_OUTPUT = auto()
    SLAB_TYPE = auto()
    EDGE = auto()
    SUPPORT_CONDITION = auto()


_ALIGNMENTS: Final = {
    "CENTER": ("Centro (center)", "centro"),
    "TOP": ("Superior (top)", "superior"),
    "BOTTOM": ("Inferior (bottom)", "inferior"),
    "LEFT": ("Esquerda (left)", "esquerda"),
    "RIGHT": ("Direita (right)", "direita"),
}
_AGGREGATES: Final = {
    "GRANITE": "Granito",
    "BASALT": "Basalto",
    "DIABASE": "Diabásio",
    "GNEISS": "Gnaisse",
    "LIMESTONE": "Calcário",
    "SANDSTONE": "Arenito",
}
_EXPOSURES: Final = {
    "WEAK": "I – Fraca",
    "MODERATE": "II – Moderada",
    "SEVERE": "III – Forte",
    "VERY_SEVERE": "IV – Muito forte",
}
_LOG_OUTPUTS: Final = {
    "CONSOLE": "Console",
    "FILE": "Arquivo",
    "BOTH": "Console e arquivo",
}
_SLAB_TYPES: Final = {
    "one_way": "Armada em uma direção",
    "two_way": "Armada em duas direções",
}
_EDGES: Final = {
    "top": "superior",
    "bottom": "inferior",
    "left": "esquerda",
    "right": "direita",
}
_SUPPORT_CONDITIONS: Final = {"fixed": "Engastada", "pinned": "Apoiada"}

# Kinds shown exactly as the engine names them (C30, CA50, PROPERTY…)
_IDENTITY: Final = frozenset(
    {OptionKind.CONCRETE, OptionKind.STEEL, OptionKind.LOG_LEVEL}
)


def _labels(kind: OptionKind) -> Mapping[str, str]:
    match kind:
        case OptionKind.ALIGNMENT:
            return {key: full for key, (full, _) in _ALIGNMENTS.items()}
        case OptionKind.MASONRY:
            return {key: full for key, (full, _) in MASONRY_LABELS.items()}
        case OptionKind.AGGREGATE:
            return _AGGREGATES
        case OptionKind.EXPOSURE:
            return _EXPOSURES
        case OptionKind.CATEGORY:
            return CATEGORY_LABELS
        case OptionKind.USAGE:
            return USAGE_LABELS
        case OptionKind.LOG_OUTPUT:
            return _LOG_OUTPUTS
        case OptionKind.SLAB_TYPE:
            return _SLAB_TYPES
        case OptionKind.EDGE:
            return _EDGES
        case OptionKind.SUPPORT_CONDITION:
            return _SUPPORT_CONDITIONS
        case OptionKind.CONCRETE | OptionKind.STEEL | OptionKind.LOG_LEVEL:
            return {}


def has_label(kind: OptionKind, key: str) -> bool:
    """Whether a key has a pt-BR label (identity kinds always do)"""
    return kind in _IDENTITY or key in _labels(kind)


def label(kind: OptionKind, key: str) -> str:
    """Return the pt-BR label of an option key, or the key itself if unknown"""
    return _labels(kind).get(key, key)


def short_label(kind: OptionKind, key: str) -> str:
    """Return the compact label used in tables (alignment, masonry), else ``label``"""
    if kind is OptionKind.ALIGNMENT and key in _ALIGNMENTS:
        return _ALIGNMENTS[key][1]
    if kind is OptionKind.MASONRY and key in MASONRY_LABELS:
        return MASONRY_LABELS[key][1]
    return label(kind, key)
