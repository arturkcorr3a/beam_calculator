from typing import Optional, List

from indeterminatebeam import Beam, Support
from indeterminatebeam.loading import Load

from properties.section_properties_calculator import SectionPropertiesCalculator
from src.properties.concrete import Concrete, concrete

# CONFIRM if these are all correct
UNITS = {'length': 'cm', 
        'force': 'kN',
        'moment': 'Nm',
        'distributed': 'N/m',
        'stiffness': 'N/m', 
        'A': 'm2', 
        'G': 'MPa', 
        'E': 'MPa',
        'I': 'cm4',
        'deflection': 'm'}

class RectangularBeam(Beam):
    """
    Extends indeterminatebeam.Beam to a rectangular cross-section beam, with necessary properties and methods for dimensioning analysis.
    """
    
    # NOTE: when change, also change in RectangularBeamBuilder
    def __init__(self, length: float, width: float, height: float, 
                 concrete: Concrete, supports: List[Support], loads: List[Load]):
        """
        Initialize a rectangular beam, with the analysis done.
        
        Args:
            length: Beam length (cm)
            width: Cross-section width (cm)
            height: Cross-section height (cm)
            fck: Concrete fck class
            supports: List of indeterminatebeam.Support instances
            loads: List of indeterminatebeam.Load instances
        """
        calculated_moment_of_inertia = SectionPropertiesCalculator.moment_of_inertia(width, height)
        area = SectionPropertiesCalculator.cross_sectional_area(width, height)
        shear_modulus = concrete.calculate_gc()
        elastic_modulus = concrete.calculate_ecs()
        super().__init__(length, shear_modulus, elastic_modulus, calculated_moment_of_inertia, area)

        self.length = length
        self.width = width
        self.height = height
        self.fck = concrete.value

        self.add_loads(loads)
        self.add_supports(supports)

        self.update_units() # TODO test these
        self.analyse()

    # TODO get_bending_moment wrapper methods (may have util methods, like max bending moment position)
    # TODO get_shear_force wrapper methods (may have util methods, like max shear force position)
    # TODO get normal_force wrapper methods (may have util methods, like max normal force position)

    def update_units(self) -> None:
        for key, unit in UNITS.items():
            super().update_units(key, unit)