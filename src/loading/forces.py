from src.elements.rectangular_beam import RectangularBeam
from src.properties.section_properties_calculator import SectionPropertiesCalculator as SPC

# TODO adicionar seção da norma disso para o #PAPER
# TODO trocar isso para lógica de escolha baseado na situação com #CAO gamma_f
LOAD_FACTOR = 1.4 

def design_effort_elu(bending_moment: float) -> float:
    """
    Calculate the design effort (ELU) by applying the load factor.
    
    :param bending_moment: Calculated bending moment
    :type bending_moment: float
    :return: Design bending moment, in the same units as input
    :rtype: float
    """
    return bending_moment * LOAD_FACTOR

def max_design_bending_moment(beam: RectangularBeam, d: int, y_max: int) -> float:
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
    uniform_stress = beam.concrete.calculate_uniform_stress() # kN/cm²
    return uniform_stress * beam.width * y_max * (d - 0.5* y_max)

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
    return 0.8 * w_0 * beam.concrete.fctk_sup # kN.cm

# TODO CQP