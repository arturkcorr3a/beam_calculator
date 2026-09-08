from src.elements.rectangular_beam import RectangularBeam
from src.properties.section_properties_calculator import (
    SectionPropertiesCalculator as SPC,
)

LOAD_FACTOR = 1.4  # ABNT NBR 6118 - Section 11.7.1 - Table 11.1 - for both permanent and variable loads
RECTANGULAR_SECTION_SHAPE_FACTOR = 1.5  # ABNT NBR 6118 - Section 17.3.1


def design_effort_elu(bending_moment: float) -> float:
    """Calculate the design effort (ELU) by applying the load factor.

    Args:
        bending_moment: Calculated bending moment in any consistent unit.

    Returns:
        Design bending moment in the same unit as input.
    """
    return bending_moment * LOAD_FACTOR


def max_design_bending_moment(beam: RectangularBeam, d: float, y_max: float) -> float:
    """Calculate the maximum design bending moment for singly reinforced rectangular beam.

    Args:
        beam: Rectangular beam section.
        d: Effective depth of the beam (cm).
        y_max: Maximum depth of the equivalent rectangular stress block (cm).

    Returns:
        Maximum design bending moment (kN.cm).
    """
    uniform_stress = beam.concrete.calculate_uniform_stress()  # kN/cm²
    return uniform_stress * beam.width * y_max * (d - 0.5 * y_max)


def min_design_bending_moment(beam: RectangularBeam) -> float:
    """Calculate the minimum design bending moment based on the minimum tension rebar area.

    Args:
        beam: Rectangular beam section.

    Returns:
        Minimum design bending moment (kN.cm).
    """
    w_0 = SPC.gross_section_modulus(beam.width, beam.height)
    return 0.8 * w_0 * beam.concrete.fctk_sup  # kN.cm


def get_almost_permanent_combination_reduction_factor(usage: str) -> float:
    # IMPLEMENT from ABNT NBR 6118 - Section 11.8.2.4 (Table 11.3) -> redirects to ABNT NBR 8681 - see how can I get it for non-residential nor commercial structures
    return 0.3


def almost_permanent_combination_els(
    permanent_load: float, variable_load: float, usage: str
) -> float:
    """Calculate the almost permanent load combination for ELS (CQP).

    Assumes a uniform usage category across the structure, yielding a single
    reduction factor (psi_2) for all variable loads.

    Args:
        permanent_load: Permanent load (kN).
        variable_load: Variable load (kN).
        usage: Usage category string used to look up psi_2.

    Returns:
        Almost permanent load combination (kN).

    References:
        ABNT NBR 6118 — Section 11.8.3.2, Table 11.4
    """
    psi_2 = get_almost_permanent_combination_reduction_factor(usage)
    return permanent_load + psi_2 * variable_load


# TODO change the way of ELU and design values: combine the actions previously to the structural analysis; use the following function when performing the structural analysis, and then take the output to calculate
def normal_elu_combination(permanent_load: float, variable_load: float) -> float:
    """Calculate the normal ELU load combination applying load factor γ_f = 1.4.

    Args:
        permanent_load: Permanent load (kN).
        variable_load: Variable load (kN).

    Returns:
        Design load combination (kN).

    References:
        ABNT NBR 6118 — Section 11.8.2.4, Table 11.3
    """
    return LOAD_FACTOR * (permanent_load + variable_load)


def calculate_cracking_moment(
    concrete_tensile_strength: float,
    distance_to_tension_fiber: float,
    moment_of_inertia: float,
) -> float:
    """Calculate the cracking moment (M_r) for a rectangular cross-section.

    Args:
        concrete_tensile_strength: Tensile strength of concrete f_ct (kN/cm²); use
            fct_m for deformation checks or fctk_inf for crack-formation checks.
        distance_to_tension_fiber: Distance from the section centroid to the most
            tensile fiber y_t (cm).
        moment_of_inertia: Gross cross-section moment of inertia I_c (cm⁴).

    Returns:
        Cracking moment M_r (kN.cm).

    References:
        ABNT NBR 6118 — Section 17.3.1
    """
    return (
        RECTANGULAR_SECTION_SHAPE_FACTOR
        * concrete_tensile_strength
        * moment_of_inertia
        / distance_to_tension_fiber
    )
