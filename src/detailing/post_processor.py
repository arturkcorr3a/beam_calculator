from __future__ import annotations

from collections.abc import Callable
from typing import TYPE_CHECKING

from src.detailing.builder import build_detailing_beam
from src.detailing.detailing_beam import DetailingBeam
from src.detailing.rounding import round_detailing
from src.logger import log_operation

if TYPE_CHECKING:
    from src.pavement_elements.continuous_beam import ContinuousBeam

# Post-processing steps, in the order they run on a freshly built detailing beam
_STEPS: tuple[Callable[[DetailingBeam], None], ...] = (round_detailing,)


def detail_beam(beam: ContinuousBeam) -> DetailingBeam:
    """Build a dimensioned beam's detailing and run the post-processing steps on it, in order

    The beam's design objects are only read; every step works on the detailing beam.

    Raises:
        ValueError: Propagated from the builder if the beam has not been dimensioned, or from a step that cannot be carried out.
    """
    detailing = build_detailing_beam(beam)
    log_operation(
        f"Detailing built: {len(detailing.bars)} bar run(s), {len(detailing.clamps)} clamp set(s), {len(detailing.stirrups)} stirrup set(s)"
    )
    for step in _STEPS:
        step(detailing)
    return detailing
