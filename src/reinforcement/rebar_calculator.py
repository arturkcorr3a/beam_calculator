from beam.rectangular_beam import RectangularBeam
from loads.internal_forces import max_design_bending_moment, design_bending_moment

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

    def update_bending_moment(self, bending_moment: float) -> None:
        """
        Update the design bending moment.
        
        :param design_bending_moment: Design bending moment
        :type design_bending_moment: float
        """
        self.design_bending_moment = design_bending_moment(bending_moment)

    def calculate(self) -> None:
        self.rebar_area = self.required_rebar_area()
        # TODO calcultions to choose rebar
        # TODO self.rebar = Rebar(...)
        
    def required_rebar_area(self) -> float:
        """
        Calculate the required rebar area for a rectangular beam, ensuring it falls within the allowable limits.
        """
        calculated_rebar_area = self.calculated_rebar_area()
        if calculated_rebar_area > self.max_rebar_area():
            raise ValueError('Required rebar area ({}) exceeds maximum allowable limit.')
        return max(calculated_rebar_area, self.min_rebar_area())

    def calculated_rebar_area(self) -> float:
        # TODO casos de armadura dupla ou simples
        pass  # FIXME implement

    def min_rebar_area(self) -> float:
        pass  # FIXME implement

    def max_rebar_area(self) -> float:
        pass  # FIXME implement

    def is_singly_reinforced(self) -> bool:
        """
        Determines if the given rectangular beam can be classified as singly reinforced for the provided design bending moment.
        
        :param beam: a rectangular beam 
        :type beam: RectangularBeam
        :param design_bending_moment: Design bending moment
        :type design_bending_moment: float
        :return: True if the beam is singly reinforced for the given design bending moment, False otherwise
        :rtype: bool
        """
        return design_bending_moment <= max_design_bending_moment(beam)
