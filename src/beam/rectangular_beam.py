from typing import Optional, List

from indeterminatebeam import Beam, Support
from indeterminatebeam.loading import Load

from properties.section_properties import moment_of_inertia, cross_sectional_area
from properties.concrete_properties import Fck


# SI Units, due to indeterminatebeam library defaults 
class RectangularBeam(Beam):
    """
    Extends indeterminatebeam.Beam to a rectangular cross-section beam, with necessary properties and methods for dimensioning analysis.
    """
    
    # NOTE: when change, also change in RectangularBeamBuilder
    def __init__(self, length: float, width: float, height: float, 
                 fck: Fck, supports: List[Support], loads: List[Load]):
        """
        Initialize a rectangular beam, with the analysis done.
        
        Args:
            length: Beam length (m)
            width: Cross-section width (m)
            height: Cross-section height (m)
            fck: Concrete fck class
            supports: List of indeterminatebeam.Support instances
            loads: List of indeterminatebeam.Load instances
        """
        calculated_moment_of_inertia = moment_of_inertia(width, height)
        area = cross_sectional_area(width, height)
        # TODO shear_modulus = TODO calculate G -> check NBR
        # TODO elastic_modulus = TODO calculate E -> check NBR
        super().__init__(length, shear_modulus, elastic_modulus, calculated_moment_of_inertia, area) #span, G, E

        self.length = length
        self.width = width
        self.height = height
        self.fck = fck.value

        self.add_loads(loads)
        self.add_supports(supports)

        self.analyse()

    # TODO get_bending_moment wrapper methods (may have util methods, like max bending moment position)
    # TODO get_shear_force wrapper methods (may have util methods, like max shear force position)
    # TODO get normal_force wrapper methods (may have util methods, like max normal force position)
    