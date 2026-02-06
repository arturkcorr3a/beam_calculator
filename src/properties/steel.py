from enum import Enum

GAMMA_S = 1.15  # CONFIRM Partial safety factor for steel

class Steel(Enum):
    """
    Possible steel yield strengths (fy) in MPa, based on ABNT NBR 6118 - Section 8.3.1.
    """
    CA25 = 250
    CA50 = 500
    CA60 = 600

    @property
    def elastic_modulus(self) -> float:
        """
        Returns the elastic modulus of steel (E_s) in MPa, based on ABNT NBR 6118 - Section 8.3.5.
        """
        return 210_000
    
    def calculate_fyd(self) -> float:
        """
        Calculates the design strength of steel (fyd) in MPa, based on ABNT NBR 6118 - Section ? 
        """ # CONFIRM section - it does not seem to be in 6118:2023
        return self.value / GAMMA_S