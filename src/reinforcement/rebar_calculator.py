from beam.rectangular_beam import RectangularBeam
from reinforcement.internal_forces import max_design_bending_moment, design_bending_moment
from src.reinforcement.reinforcement import Reinforcement
from typing import Optional

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

    def update_bending_moment(self, bending_moment: float) -> None:
        """
        Updates the bending moment for rebar calculation.
        
        :param bending_moment: Design bending moment
        :type bending_moment: float
        """
        self.design_bending_moment = design_bending_moment(bending_moment)

    def calculate(self) -> None:
        self.rebar_area = self.calculate_required_rebar_area()
        pass  # IMPLEMENT
        # TODO calcultions to choose rebar
        # TODO self.rebar = Rebar(...)
        
    def calculate_required_rebar_area(self) -> float:
        """
        Calculate the required rebar area for a rectangular beam, ensuring it falls within the allowable limits.
        """
        calculated_rebar_area = self.calculate_rebar_area()
        minimum_rebar_area = self.calculate_min_tension_rebar_area()
        maximum_rebar_area = self.calculate_max_rebar_area()

        if calculated_rebar_area > maximum_rebar_area:
            raise ValueError('Required rebar area exceeds maximum allowable limit.')
        return max(calculated_rebar_area, minimum_rebar_area)

    def calculate_rebar_area(self) -> float:
        if self.is_singly_reinforced:
            return self.calculate_single_reinforcement_rebar_area()
        return self.calculate_double_reinforcement_rebar_area()

    def calculate_single_reinforcement_rebar_area(self) -> float:
        pass # IMPLEMENT

    def calculate_double_reinforcement_rebar_area(self) -> float:
        pass # IMPLEMENT

    def calculate_min_tension_rebar_area(self) -> float:
        """
        Minimum tension rebar area, according to ABNT NBR 6118 - Section 17.3.5.2.1
        """
        # apenas para armadura de tração
        pass  # IMPLEMENT

    def calculate_max_rebar_area(self) -> float:
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
        Calculates the 
        """
        lambda_c = self.beam.concrete.calculate_lambda_c()
        epsilon_cu = self.beam.concrete.calculate_epsilon_cu()
        steel_elastic_modulus = self.beam.steel.elastic_modulus
        fyd = self.beam.steel.calculate_fyd()
        d = self.calculate_effective_depth() # CONFIRM if this makes sense 
        return lambda_c * ( (epsilon_cu*steel_elastic_modulus) / (fyd + epsilon_cu*steel_elastic_modulus) ) * d
    
    def calculate_effective_depth(self) -> float:
        """
        Calculates the effective depth (d) of the beam, considering the nominal covering and reinforcements.
        """
        covering = self.beam.nominal_covering
        if self.rebar is None:
            return self.beam.height - covering # FIXME find heuristic for first guess
        return self.beam.height - covering - self.rebar.get_distance_for_effective_depth_calculation() # CONFIRM if this makes sense after Reinforcement class full implementation