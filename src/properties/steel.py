from enum import Enum
from typing import List

GAMMA_S = 1.15  # CONFIRM Partial safety factor for steel

class Steel(Enum):
    """
    Possible steel yield strengths (fy) in MPa, based on ABNT NBR 6118 - Section 8.3.1.
    """
    CA25 = 250
    CA50 = 500
    CA60 = 600

    @property
    def elastic_modulus(self) -> int:
        """
        Returns the elastic modulus of steel (E_s) in MPa, based on ABNT NBR 6118 - Section 8.3.5.
        """
        return 210_000
    
    @property
    def fyd(self) -> float:
        """
        The design strength of steel (fyd) in MPa, based on ABNT NBR 6118 - Section ? 
        """ # CONFIRM section - it does not seem to be in 6118:2023
        return self.value / GAMMA_S
    
    # CONFIRM these sizes, they are probably wrong
    def available_sizes(self) -> List[int]:
        match self.name:
            case Steel.CA25:
                return [5, 8, 10, 12.5, 16, 20, 25, 32, 40]
            case Steel.CA60:
                return [5, 8, 10, 12.5, 16, 20, 25, 32, 40]
            case Steel.CA60:
                return [5, 8, 10, 12.5, 16, 20, 25, 32, 40]
        return []