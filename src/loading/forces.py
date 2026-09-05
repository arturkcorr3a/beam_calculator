from src.elements.rectangular_beam import RectangularBeam
from src.properties.section_properties_calculator import (
    SectionPropertiesCalculator as SPC,
)

LOAD_FACTOR = 1.4  # ABNT NBR 6118 - Section 11.7.1 - Table 11.1 - for both permanent and variable loads
RECTANGULAR_SECTION_SHAPE_FACTOR = 1.5  # ABNT NBR 6118 - Section 17.3.1


def design_effort_elu(bending_moment: float) -> float:
    """
    Calculate the design effort (ELU) by applying the load factor.

    :param bending_moment: Calculated bending moment
    :type bending_moment: float
    :return: Design bending moment, in the same units as input
    :rtype: float
    """
    return bending_moment * LOAD_FACTOR


def max_design_bending_moment(beam: RectangularBeam, d: float, y_max: float) -> float:
    """
    Calculates the maximum design bending moment for which a given rectangular beam can be singly reinforced.

    :param beam: a rectangular beam
    :type beam: RectangularBeam
    :param d: effective depth of the beam (cm)
    :type d: int
    :param y_max: maximum depth of the equivalent rectangular stress block (cm)
    :type y_max: int
    :return: Maximum design bending moment, in kN.cm
    :rtype: float
    """
    uniform_stress = beam.concrete.calculate_uniform_stress()  # kN/cm²
    return uniform_stress * beam.width * y_max * (d - 0.5 * y_max)


def min_design_bending_moment(beam: RectangularBeam) -> float:
    """
    Calculates the minimum design bending moment for which a given rectangular beam can be singly reinforced, based on the minimum tension rebar area.

    :param beam: a rectangular beam
    :type beam: RectangularBeam
    :param d: effective depth of the beam (cm)
    :type d: int
    :return: Minimum design bending moment, in kN.cm
    :rtype: float
    """
    w_0 = SPC.gross_section_modulus(beam.width, beam.height)
    return 0.8 * w_0 * beam.concrete.fctk_sup  # kN.cm


def get_almost_permanent_combination_reduction_factor(usage: str) -> float:
    # IMPLEMENT from ABNT NBR 6118 - Section 11.8.2.4 (Table 11.3) -> redirects to ABNT NBR 8681
    # IMPLEMENT see how can I get it for non-residential nor commercial structures
    return 0.3


def almost_permanent_combination_els(
    permanent_load: float, variable_load: float, usage: str
) -> float:
    """
    Calculates the almost permanent combination of loads for the service limit state (ELS - CQP).
    According to ABNT NBR 6118 - Section 11.8.3.2 - Table 11.4.

    This function considers that the usage category is the same for all the structure, therefore having an unique reduction factor (psi_2) for all variable loads.

    :param permanent_load: Permanent load (kN)
    :type permanent_load: float
    :param variable_load: Variable load (kN)
    :type variable_load: float
    :return: Almost permanent combination of loads, in kN
    :rtype: float
    """
    psi_2 = get_almost_permanent_combination_reduction_factor(usage)
    return permanent_load + psi_2 * variable_load


# TODO change the way of ELU and design values: combine the actions previously to the structural analysis; use the following function when performing the structural analysis, and then take the output to calculate
def normal_elu_combination(permanent_load: float, variable_load: float) -> float:
    """
    Calculates the normal combination of loads for the ultimate limit state (ELU).
    According to ABNT NBR 6118 - Section 11.8.2.4 - Table 11.3.

    This function considers the usage of the full resistant capacity of the structure.

    :param permanent_load: Permanent load (kN)
    :type permanent_load: float
    :param variable_load: Variable load (kN)
    :type variable_load: float
    :return: Normal combination of loads, in kN
    :rtype: float
    """
    return LOAD_FACTOR * (permanent_load + variable_load)


def calculate_cracking_moment(
    concrete_tensile_strength: float,
    distance_to_tension_fiber: float,
    moment_of_inertia: float,
) -> float:
    """
    Calculates the cracking moment (M_r) for a rectangular cross-section.
    According to ABNT NBR 6118 - Section 17.3.1.

    :param concrete_tensile_strength: Concrete tensile strength (f_ct), e.g., fct_m, for deformation verification or fctk_inf, for crack-formation verification (kN/cm²)
    :type concrete_tensile_strength: float
    :param distance_to_tension_fiber: Distance from the center of gravity of the cross-section to the most tensile fiber (y_t) (cm)
    :type distance_to_tension_fiber: float
    :param moment_of_inertia: Moment of inertia of the gross cross-section (I_c) (cm⁴)
    :type moment_of_inertia: float
    :return: Cracking moment (M_r), in kN.cm
    :rtype: float
    """
    return (
        RECTANGULAR_SECTION_SHAPE_FACTOR
        * concrete_tensile_strength
        * moment_of_inertia
        / distance_to_tension_fiber
    )
