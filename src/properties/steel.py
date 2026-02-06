from enum import Enum



class Steel(Enum):
    """
    Possible steel yield strengths (fy) in MPa, based on ABNT NBR 6118 - Section 8.3.1.
    """
    CA25 = 250
    CA50 = 500
    CA60 = 600

class SteelPropertiesCalculator:
    """
    Calculates properties specific to steel reinforcement.
    """
    pass