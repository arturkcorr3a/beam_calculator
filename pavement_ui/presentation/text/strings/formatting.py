"""Fragments used by the formatting functions (notation and joins)."""

from typing import Final

PHI: Final = "Φ"
NONE: Final = "—"
GROUP_JOIN: Final = " + "
LAYER_JOIN: Final = " · "
LAYER_ITEM: Final = "Camada {index}: {bars}"
STIRRUP: Final = "{phi}{diameter} c/{spacing} cm"
STIRRUP_PREFIXED: Final = "Estribo: {stirrup}"

MOMENT_POSITIVE: Final = "M+"
MOMENT_NEGATIVE: Final = "M\N{MINUS SIGN}"
POINT_SPAN: Final = "Vão {ref} ({sign})"
POINT_SUPPORT: Final = "Apoio {ref} ({sign})"

CHAIN_JOIN: Final = " – "
DIMS: Final = "{lx} × {ly}"

COUNT_JOIN: Final = " · "
PILLAR_SINGULAR: Final = "pilar"
PILLAR_PLURAL: Final = "pilares"
BEAM_SINGULAR: Final = "viga"
BEAM_PLURAL: Final = "vigas"
SLAB_SINGULAR: Final = "laje"
SLAB_PLURAL: Final = "lajes"
