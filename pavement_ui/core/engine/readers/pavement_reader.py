"""Read a resolved pavement into a DesignSuccess."""

from pavement_ui.core.engine.readers.beam_reader import read_beam
from pavement_ui.core.engine.readers.slab_reader import read_slab
from pavement_ui.core.results.outcomes import DesignSuccess
from src.pavement_elements.pavement import Pavement


def read(pavement: Pavement) -> DesignSuccess:
    """Read every beam and slab, in registration order"""
    return DesignSuccess(
        beams=tuple(read_beam(b, pavement.pillars) for b in pavement.beams.values()),
        slabs=tuple(read_slab(s) for s in pavement.slabs.values()),
    )
