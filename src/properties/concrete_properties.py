from enum import Enum

# TODO conferir se esses valores de fck batem com a norma
class Fck(Enum):
    """
    Possible concrete characteristic compressive strengths (fck) in MPa.
    """
    C25 = 25
    C30 = 30
    C35 = 35
    C40 = 40
    C45 = 45
    C50 = 50
    C55 = 55
    C60 = 60
    C65 = 65
    C70 = 70
    C75 = 75
    C80 = 80
    C85 = 85
    C90 = 90

class ConcretePropertiesCalculator:
    pass  # FIXME implement using @staticmethod