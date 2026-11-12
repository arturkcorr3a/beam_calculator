"""Read a resolved pavement into a DesignSuccess."""

from pavement_ui.core.engine.readers.beam_reader import read_beam
from pavement_ui.core.engine.readers.materials_reader import read_materials
from pavement_ui.core.engine.readers.quantities_reader import read_quantities
from pavement_ui.core.engine.readers.slab_reader import read_slab
from pavement_ui.core.results.outcomes import DesignSuccess
from src.pavement_elements.pavement import Pavement


def read(pavement: Pavement, name: str | None = None) -> DesignSuccess:
    """Read every beam and slab, in registration order, the beams' quantities and the materials

    Must run while APP_CONFIG holds the design settings.

    Args:
        name: Pavement name for the detailing sheets' title blocks.
    """
    total = sum(beam.detailing is not None for beam in pavement.beams.values())
    numbers = iter(range(1, total + 1))
    return DesignSuccess(
        beams=tuple(
            read_beam(
                b,
                pavement.pillars,
                name,
                next(numbers) if b.detailing is not None else 1,
                total,
            )
            for b in pavement.beams.values()
        ),
        slabs=tuple(read_slab(s, pavement.pillars) for s in pavement.slabs.values()),
        quantities=read_quantities(pavement),
        materials=read_materials(),
    )
