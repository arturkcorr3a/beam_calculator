from enum import Enum
from math import sqrt, cbrt

GAMMA_C = 1.4  # CONFIRM Partial safety factor for concrete 

class Concrete(Enum):
    """
    Possible concrete characteristic compressive strengths (fck) in MPa and its properties.
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

    def get_concrete_group(self) -> int:
        """
        Based on ABNT NBR 8953 concrete groups classification.
        """
        if self.value > 50:
            return 2
        return 1
    
    def calculate_eci(self) -> float:
        """
        Calculates the initial elastic modulus of concrete (E_ci) in MPa, based on ABNT NBR 6118 - Section 8.2.8, for granite and gneiss aggregate.
        """
        alpha_e = 1,0 # for granite and gneiss aggregate
        concrete_group = self.get_concrete_group()
        if concrete_group == 1:
            return alpha_e * 5600 * sqrt(self.value)
        return 21.5 * 10**3 * alpha_e * cbrt(self.value / 10 + 1.25)
            
    def calculate_ecs(self) -> float:
        """
        Calculates the secant elastic modulus of concrete (E_cs) in MPa, based on ABNT NBR 6118 - Section 8.2.8, for granite and gneiss aggregate.
        """
        alpha_i = 0.8 + 0.2 * (self.value / 80)
        alpha_i = min(alpha_i, 1.0)
        eci = self.calculate_eci()
        return alpha_i * eci
    
    def calculate_gc(self) -> float:
        """
        Calculates the shear modulus of concrete (G_c) in MPa, based on ABNT NBR 6118 - Section 8.2.9, for granite and gneiss aggregate.
        """
        ecs = self.calculate_ecs()
        return ecs / 2.4 # assuming poisson's ratio of 0.2
    
    def calculate_alpha_c(self) -> float:
        """
        Calculates the Rüsch effect factor (alpha_c) for concrete, based on ABNT NBR 6118 - Section 17.2.2.
        """
        if self.value <= 50:
            return 0.85
        return 0.85 * (1.0 - (self.value - 50) / 200)
    
    def calculate_eta_c(self) -> float:
        """
        Calculates the brittleness factor (eta_c) for concrete, based on ABNT NBR 6118 - Section 8.2.10.1.
        """
        if self.value <= 40:
            return 1.0
        return cbrt(40.0/self.value)
    
    def calculate_fcd(self) -> float:
        """
        Calculates the design compressive strength of concrete (fcd) in MPa, based on ABNT NBR 6118 - Section 12.3.3. Considers only normal action combinations (fator 1.4)
        """
        return self.value / GAMMA_C
    
    def calculate_uniform_stress(self) -> float:
        """
        Calculates the equivalent uniform stress in concrete in MPa, based on ABNT NBR 6118 - Section 17.2.2.
        """
        alpha_c = self.calculate_alpha_c()
        eta_c = self.calculate_eta_c()
        fcd = self.calculate_fcd()
        return alpha_c * eta_c * fcd
    
    def calculate_lambda_c(self) -> float:
        """
        Calculates the stress block depth factor (lambda) based on ABNT NBR 6118 - Section 17.2.2.

        This factor defines the ratio between the depth of the equivalent rectangular 
        stress block (y) and the actual neutral axis depth (x).
        """
        if self.value <= 50:
            return 0.8
        return 0.8 - (self.value - 50) / 400
    
    def calculate_epsilon_c2(self) -> float:
        """
        Calculates the compressive strain at the onset of the plastic plateau of concrete (epsilon_c2) based on ABNT NBR 6118 - Section 8.10.1.
        """
        if self.value <= 50:
            return 2e-3
        return 2e-3 + 0.085e-3 * (self.value - 50)**0.53
    
    def calculate_epsilon_cu(self) -> float:
        """
        Calculates the ultimate compressive strain of concrete (epsilon_cu) based on ABNT NBR 6118 - Section 8.10.1.
        """
        if self.value <= 50:
            return 3.5e-3
        return 2.6e-3 + 35e-3 * ((90 - self.value)/100)**4