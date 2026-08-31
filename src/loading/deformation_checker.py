
from dataclasses import dataclass

from src.loading.forces import almost_permanent_combination_els


@dataclass
class DeformationChecker:
    """
    Excessive deformation verification for linear elements, according to ELS (Service Limit State) criteria, based on ABNT NBR 8681 - Section 7.3.2.

    For slabs (superficial elements), ABNT NBR 6118 - Section 19.3.1, redirects to the linear elements verification
    """
    permanent_load: float  # kN/m
    variable_load: float   # kN/m
    usage: str

    @property
    def design_load(self) -> float:
        """
        Calculates the design load for the element, based on the almost permanent combination of loads, according to ABNT NBR 6118 - Section 11.8.3.1 - item a. 
        """
        return almost_permanent_combination_els(self.permanent_load, self.variable_load, self.usage)

    def verify(self) -> bool:
        """
        Verifies if the deformation of the element is within acceptable limits.

        :return: True if the deformation is acceptable, False otherwise
        :rtype: bool
        """
        # IMPLEMENT and update docstring
        return True