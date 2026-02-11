from beam.rectangular_beam import RectangularBeam
from reinforcement.internal_forces import max_design_bending_moment, design_bending_moment
from src.reinforcement.reinforcement import Reinforcement
from typing import Optional
from math import sqrt
from functools import cached_property

# TODO review how many times each method/property is called to evaluate propper use of cached or calculated properties
class RebarCalculator:
    """
    Class responsible for calculating the required rebar area for a rectangular beam.
    """
    
    def __init__(self, beam: RectangularBeam, bending_moment: float):
        """
        Initialize the RebarCalculator with a rectangular beam and its design bending moment.
        
        :param beam: a rectangular beam 
        :type beam: RectangularBeam
        :param design_bending_moment: Design bending moment
        :type design_bending_moment: float
        """
        self.beam = beam
        self.design_bending_moment = design_bending_moment(bending_moment)
        self.rebar: Optional[Reinforcement] = None
        self.calculate()

    def update_bending_moment(self, bending_moment: float) -> None:
        """
        Updates the bending moment for rebar calculation.
        
        :param bending_moment: Design bending moment
        :type bending_moment: float
        """
        self.design_bending_moment = design_bending_moment(bending_moment)
        del self.max_bending_moment
        self.calculate()

    def calculate(self) -> None:
        self.calculate_and_set_required_reinforcement()
        # TODO choose rebars
        # TODO recalculate with effective d and d' from chosen rebars
        
    def calculate_and_set_required_reinforcement(self) -> None:
        """
        Calculate the required rebar area for a rectangular beam, ensuring it falls within the allowable limits.
        """
        self.tensioned_rebar_area = max(self.tensioned_rebar_area, self.min_tension_rebar_area) 
        if (self.tensioned_rebar_area + self.compressed_rebar_area) > self.max_rebar_area:
            raise ValueError('Required rebar area exceeds maximum allowable limit.')

    @property
    def min_tension_rebar_area(self) -> float:
        """
        Minimum tension rebar area, according to ABNT NBR 6118 - Section 17.3.5.2.1
        """
        # apenas para armadura de tração
        pass  # IMPLEMENT

    @property
    def max_rebar_area(self) -> float:
        """
        Maximum rebar area according to ABNT NBR 6118 - Section 17.3.5.2.4
        """
        # 4 per cent of cross-sectional area
        return 0.04 * self.beam._A 

    @property
    def is_singly_reinforced(self) -> bool:
        """
        Determines if the given rectangular beam can be classified as singly reinforced for the provided design bending moment.
        """
        return self.design_bending_moment <= max_design_bending_moment(self.beam)
    
    def calculate_y_limit(self) -> float:
        """
        Calculates the maximmum depth of the equivalent rectangular stress block to maintain the deformation domain 3 (the limit is to turn to 4, as domain 2 would also be ok), based on ABNT NBR 6118 - Section 17.2.2. 
        """
        lambda_c = self.beam.concrete.lambda_c()
        epsilon_cu = self.beam.concrete.epsilon_cu()
        steel_elastic_modulus = self.beam.steel.elastic_modulus
        fyd = self.beam.steel.fyd()
        d = self.d() # CONFIRM if this makes sense 

        return lambda_c * ( (epsilon_cu*steel_elastic_modulus) / (fyd + epsilon_cu*steel_elastic_modulus) ) * d
    
    def calculate_max_y_ductility(self) -> float:
        """
        Maximum depth of the equivalent rectangular stress block (y) to maintain ductility, based on ABNT NBR 6118 - Section 14.6.4.3.
        """
        if self.beam.concrete.value <= 50:
            return 0.45 * self.beam.concrete.lambda_c() * self.d()
        return 0.35 * self.beam.concrete.lambda_c() * self.d()
    
    @cached_property
    def max_y(self) -> float:
        """
        Calculates the maximum depth of the equivalent rectangular stress block (y) to maintain both the deformation domain 3 and ductility.
        """
        return min(self.calculate_y_limit(), self.calculate_max_y_ductility())    
    
    @cached_property
    def d(self) -> float:
        """
        Calculates the effective depth (d) of the beam, considering the nominal covering and reinforcements.
        """
        covering = self.beam.nominal_covering
        if self.rebar is None:
            return self.beam.height - covering - 1.25/2# FIXME find heuristic for first guess
        return self.beam.height - covering - self.rebar.get_distance_for_d_calculation() # CONFIRM if this makes sense after Reinforcement class full implementation
    
    @cached_property
    def max_bending_moment(self) -> float:
        """
        Calculates the maximum bending moment that the beam can resist with single reinforcement, for the current rebar configuration (due to effective depth and maximum y)
        """ # CONFIRM the return units
        alpha_c = self.beam.concrete.alpha_c
        eta_c = self.beam.concrete.eta_c
        fcd = self.beam.concrete.fcd
        bw = self.beam.width
        y_max = self.max_y()
        d = self.d()
        return alpha_c * eta_c * fcd * bw * y_max * (d - y_max * 0.5)

    def calculate_actual_y(self) -> float:
        """
        Calculates the actual depth of the equivalent rectangular stress block (y) (cm) for the current effective depth and design bending moment. Based on equilibrium of internal forces and moment.
        """
        d = self.d()
        alpha_c = self.beam.concrete.alpha_c
        eta_c = self.beam.concrete.eta_c
        fcd = self.beam.concrete.fcd
        bw = self.beam.width
        return d - sqrt(d**2 - (2 * self.design_bending_moment)/(alpha_c * eta_c * fcd * bw))
    
    @cached_property
    def as1(self) -> float:
        """
        Calculates the required tensioned rebar area (As1) for the current design bending moment, based on the actual depth of the equivalent rectangular stress block (y) and equilibrium of internal forces.
        """ # CONFIRM the return units
        alpha_c = self.beam.concrete.alpha_c
        eta_c = self.beam.concrete.eta_c
        fcd = self.beam.concrete.fcd
        bw = self.beam.width
        y = self.calculate_actual_y() if self.is_singly_reinforced else self.max_y()
        return (alpha_c * eta_c * fcd * bw * y) / (self.beam.steel.fyd())
    
    def calculate_epsilon_s2(self) -> float:
        # TODO docstring
        epsilon_cu = self.beam.concrete.epsilon_cu
        lambda_c = self.beam.concrete.lambda_c
        max_y = self.max_y()
        return epsilon_cu * (max_y - lambda_c * self.d_compressed()) / max_y

    @cached_property
    def d_compressed(self) -> float:
        """
        Calculates the distance from the extreme compression fiber to the centroid of the compressed rebar (d'), considering the current rebar configuration.
        """
        covering = self.beam.nominal_covering
        if self.rebar is None:
            return covering + 1.25/2 # FIXME find heuristic for first guess
        return covering + self.rebar.get_distance_for_compressed_d_calculation() # CONFIRM if this makes sense after Reinforcement class full implementation
    
    def calculate_sigma_s2(self) -> float:
        # TODO docstring
        calculated_sigma_s2 = self.calculate_epsilon_s2() * self.beam.steel.elastic_modulus
        max_sigma_s2 = self.beam.steel.fyd()
        return min(calculated_sigma_s2, max_sigma_s2)

    @cached_property
    def corrected_sigma_s2(self) -> float:
        # TODO docstring
        sigma_s2 = self.calculate_sigma_s2()
        return sigma_s2 - self.beam.concrete.calculate_uniform_stress()

    def calculate_delta_bending_moment(self) -> float:
        # TODO docstring
        return self.design_bending_moment - self.max_bending_moment

    @cached_property
    def compressed_rebar_area(self) -> float:
        # TODO docstring
        delta_moment = self.calculate_delta_bending_moment()
        return delta_moment / (self.corrected_sigma_s2 * (self.d() - self.d_compressed()))
    
    def calculate_delta_as(self) -> float:
        # TODO docstring
        return self.compressed_rebar_area * (self.beam.steel.fyd() / self.corrected_sigma_s2) # CONFIRM the formula -> acho q ta errado

    @cached_property
    def tensioned_rebar_area(self) -> float:
        # TODO docstring
        return self.as1 + self.calculate_delta_as() if not self.is_singly_reinforced else self.as1