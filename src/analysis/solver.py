from src.analysis.beam_analysis import BeamAnalysis
from src.analysis.indeterminatebeam_analysis import IndeterminateBeamAnalysis
from src.analysis.model import BeamSupport, DistributedLoad
from src.structural_elements.rectangular_beam import RectangularBeam


def analyse_beam(
    section: RectangularBeam,
    supports: list[BeamSupport],
    loads: list[DistributedLoad],
) -> BeamAnalysis:
    """Solve a beam with the project's structural solver.

    This is the single place that chooses the solver implementation.
    """
    return IndeterminateBeamAnalysis(section, supports, loads)
