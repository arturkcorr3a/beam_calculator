from enum import Enum
from math import sqrt, cbrt

class Fck(Enum):
    """
    Possible concrete characteristic compressive strengths (fck) in MPa.
    """
    C20 = 20
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

# IMPLEMENT using @staticmethod
class ConcretePropertiesCalculator:

    @staticmethod
    def get_concrete_group(fck: Fck) -> int:
        """
        Based on ABNT NBR 8953 concrete groups classification.
        """
        if fck.value > 50:
            return 2
        return 1
    
    @staticmethod
    def calculate_eci(fck: Fck) -> float:
        """
        Calculate the initial elastic modulus of concrete (E_ci) in MPa, based on ABNT NBR 6118 - Section 8.2.8, for granite and gneiss aggregate.
        """
        alpha_e = 1,0 # for granite and gneiss aggregate
        concrete_group = ConcretePropertiesCalculator.get_concrete_group(fck)
        if concrete_group == 1:
            return alpha_e * 5600 * sqrt(fck.value)
        return 21.5 * 10**3 * alpha_e * cbrt(fck.value / 10 + 1.25)
            
    @staticmethod
    def calculate_ecs(fck: Fck) -> float:
        """
        Calculate the secant elastic modulus of concrete (E_cs) in MPa, based on ABNT NBR 6118 - Section 8.2.8, for granite and gneiss aggregate.
        """
        alpha_i = 0.8 + 0.2 * (fck.value / 80)
        alpha_i = min(alpha_i, 1.0)
        eci = ConcretePropertiesCalculator.calculate_eci(fck)
        return alpha_i * eci
    
    @staticmethod
    def calculate_gc(fck: Fck) -> float:
        """
        Calculate the shear modulus of concrete (G_c) in MPa, based on ABNT NBR 6118 - Section 8.2.9, for granite and gneiss aggregate.
        """
        ecs = ConcretePropertiesCalculator.calculate_ecs(fck)
        return ecs / 2.4 # assuming poisson's ratio of 0.2