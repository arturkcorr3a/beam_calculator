from dataclasses import dataclass

from src.analysis.beam_analysis import BeamAnalysis
from src.analysis.model import BeamSupport, DistributedLoad
from src.analysis.solver import analyse_beam
from src.calculators.rebar_calculator import RebarCalculator
from src.calculators.stirrup_calculator import StirrupCalculator
from src.calculators.stirrup_rebar_coordinator import coordinate_span
from src.loading.forces import design_effort_elu
from src.loading.linear_loads import LinearLoads
from src.logger import log_general
from src.reinforcement.stirrups import Stirrups
from src.structural_elements.rectangular_beam import RectangularBeam


@dataclass(frozen=True, slots=True)
class SimplySupportedBeamDesign:
    """Dimensioning of a simply supported beam loaded only by its own weight

    Attributes:
        section: The dimensioned beam section.
        self_weight: Own-weight distributed load (kN/m).
        analysis: Structural analysis of the beam (positions in cm).
        calculator: Longitudinal reinforcement calculator at the greatest moment.
        stirrups: Stirrups chosen for the whole beam.
        characteristic_shear_force: Greatest |V| along the beam (kN).
    """

    section: RectangularBeam
    self_weight: float
    analysis: BeamAnalysis
    calculator: RebarCalculator
    stirrups: Stirrups
    characteristic_shear_force: float


def design_simply_supported_beam(section: RectangularBeam) -> SimplySupportedBeamDesign:
    """Dimension a simply supported beam under its own weight

    Supports are pinned at both ends; the longitudinal reinforcement is
    dimensioned at the greatest bending moment and coordinated with the
    stirrups, as a single span.

    Args:
        section: Beam section; its length is the span (cm).

    Returns:
        The analysis, reinforcement and stirrups of the beam.

    Raises:
        ValueError: If the section cannot be dimensioned (propagated from the
            calculators, e.g. V_Sd above V_Rd2 or As above the maximum).
    """
    log_general("Simply supported beam dimensioning starting")
    length = section.length  # cm
    self_weight = LinearLoads.get_concrete_element_own_weight(
        section.width * section.height / 10_000
    )  # kN/m, from a cm² area converted to m²
    analysis = analyse_beam(
        section,
        [BeamSupport(0.0), BeamSupport(length)],
        [DistributedLoad(0.0, length, self_weight)],
    )

    position, moment = analysis.moment_extreme_in_range(0.0, length)  # cm, kN.m
    shear_force = analysis.max_abs_shear()  # kN
    stirrups = Stirrups(
        section,
        StirrupCalculator(section, design_effort_elu(shear_force), section.label),
        section.label,
    )
    calculator = RebarCalculator(
        beam=section,
        bending_moment=moment,
        bending_moment_position=position,
        id=section.label,
    )
    coordinate_span([calculator], stirrups)

    return SimplySupportedBeamDesign(
        section=section,
        self_weight=self_weight,
        analysis=analysis,
        calculator=calculator,
        stirrups=stirrups,
        characteristic_shear_force=shear_force,
    )
