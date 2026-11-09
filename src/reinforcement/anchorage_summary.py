"""Final anchorage values of one bar layer towards one side."""

from dataclasses import dataclass
from typing import Literal

type AnchorageSide = Literal["left", "right"]


@dataclass(frozen=True, slots=True)
class AnchorageSummary:
    """Anchorage lengths of a layer's bars once its anchorage is resolved

    Attributes:
        layer_index: Index of the layer in the reinforcement (0 is the outermost).
        side: Side of the interest point the bars are anchored towards.
        basic_length: Basic anchorage length l_b (cm).
        necessary_length: Necessary anchorage length l_b,nec (cm), with the
            hook coefficient of the final bars.

    References:
        ABNT NBR 6118:2026 — Sections 9.4.2.4 and 9.4.2.5
    """

    layer_index: int
    side: AnchorageSide
    basic_length: float
    necessary_length: float
