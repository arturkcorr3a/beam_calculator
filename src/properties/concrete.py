# cSpell:ignore cbrt
from enum import Enum
from math import cbrt, log, sqrt
from typing import cast

from src.logger import log_property, logger_label

GAMMA_C = 1.4  # ABNT NBR 6118 - Section 12.4.1


@logger_label("Concrete {name}")
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

    @property
    def concrete_group(self) -> int:
        """
        Based on ABNT NBR 8953 concrete groups classification.
        """
        result = 2 if self.value > 50 else 1
        log_property(f"concrete group: {result}")
        return result

    @property
    def eci(self) -> float:
        """
        The initial elastic modulus of concrete (E_ci) in MPa, based on ABNT NBR 6118 - Section 8.2.8, for granite and gneiss aggregate.
        """
        alpha_e = 1.0  # for granite and gneiss aggregate
        if self.concrete_group == 1:
            result = alpha_e * 5600 * sqrt(self.value)
            log_property(f"E_ci = {result:.2f} MPa")
            return result
        eci = 21.5 * 10**3 * alpha_e * cbrt(self.value / 10 + 1.25)
        log_property(f"E_ci = {eci:.2f} MPa")
        return eci

    @property
    def ecs(self) -> float:
        """
        The secant elastic modulus of concrete (E_cs) in MPa, based on ABNT NBR 6118 - Section 8.2.8, for granite and gneiss aggregate.
        """
        alpha_i = 0.8 + 0.2 * (self.value / 80)
        alpha_i = min(alpha_i, 1.0)
        result = alpha_i * self.eci
        log_property(f"alpha_i = {alpha_i:.4f} → E_cs = {result:.2f} MPa")
        return result

    @property
    def g_c(self) -> float:
        """
        The shear modulus of concrete (G_c) in MPa, based on ABNT NBR 6118 - Section 8.2.9, for granite and gneiss aggregate.
        """
        ecs = self.ecs
        result = ecs / 2.4  # assuming poisson's ratio of 0.2
        log_property(f"G_c = E_cs/2.4 = {result:.2f} MPa")
        return result

    @property
    def alpha_c(self) -> float:
        """
        The Rüsch effect factor (alpha_c) for concrete, based on ABNT NBR 6118 - Section 17.2.2.
        """
        if self.value <= 50:
            result = 0.85
        else:
            result = 0.85 * (1.0 - (self.value - 50) / 200)
        log_property(f"alpha_c = {result:.4f}")
        return result

    @property
    def eta_c(self) -> float:
        """
        The brittleness factor (eta_c) for concrete, based on ABNT NBR 6118 - Section 8.2.10.1.
        """
        if self.value <= 40:
            result = 1.0
        else:
            result = cbrt(40.0 / self.value)
        log_property(f"eta_c = {result:.4f}")
        return result

    @property
    def fcd(self) -> float:
        """
        The design compressive strength of concrete (fcd) in kN/cm², based on ABNT NBR 6118 - Section 12.3.3. Considers only normal action combinations (factor 1.4)
        """
        result = (self.value / 10) / GAMMA_C
        log_property(f"fcd = {result:.4f} kN/cm²")
        return result

    def calculate_uniform_stress(self) -> float:
        """
        Calculates the equivalent uniform stress in concrete in kN/cm², based on ABNT NBR 6118 - Section 17.2.2.
        """
        alpha_c = self.alpha_c
        eta_c = self.eta_c
        fcd = self.fcd
        result = alpha_c * eta_c * fcd
        log_property(
            f"uniform stress = alpha_c({alpha_c:.4f}) × eta_c({eta_c:.4f}) × fcd({fcd:.4f}) = {result:.4f} kN/cm²"
        )
        return result

    @property
    def lambda_c(self) -> float:
        """
        The stress block depth factor (lambda) based on ABNT NBR 6118 - Section 17.2.2.

        This factor defines the ratio between the depth of the equivalent rectangular stress block (y) and the actual neutral axis depth (x).
        """
        if self.value <= 50:
            result = 0.8
        else:
            result = 0.8 - (self.value - 50) / 400
        log_property(f"lambda_c = {result:.4f}")
        return result

    @property
    def epsilon_c2(self) -> float:
        """
        The compressive strain at the onset of the plastic plateau of concrete (epsilon_c2) based on ABNT NBR 6118 - Section 8.10.1.
        """
        if self.value <= 50:
            result = 2e-3
        else:
            result = cast(float, 2e-3 + 0.085e-3 * (self.value - 50) ** 0.53)
        log_property(f"epsilon_c2 = {result:.6f}")
        return result

    @property
    def epsilon_cu(self) -> float:
        """
        Ultimate compressive strain of concrete (epsilon_cu) based on ABNT NBR 6118 - Section 8.10.1.
        """
        if self.value <= 50:
            result = 3.5e-3
        else:
            result = 2.6e-3 + 35e-3 * ((90 - self.value) / 100) ** 4
        log_property(f"epsilon_cu = {result:.6f}")
        return result

    @property
    def fct_m(self) -> float:
        """
        The mean tensile strength of concrete (fct_m) in kN/cm², based on ABNT NBR 6118 - Section 8.2.5.
        """
        if self.value <= 50:
            result = (0.3 * self.value ** (2 / 3)) / 10
        else:
            result = (2.12 * log(1 + 0.1 * (self.value + 8))) / 10
        log_property(f"fct_m = {result:.4f} kN/cm²")
        return result

    @property
    def fctk_sup(self) -> float:
        """
        The upper characteristic tensile strength of concrete (f_ctk_sup) in kN/cm², based on ABNT NBR 6118 - Section 8.2.5.
        """
        result = 1.3 * self.fct_m
        log_property(f"fctk_sup = 1.3 × fct_m = {result:.4f} kN/cm²")
        return result

    @property
    def fctk_inf(self) -> float:
        """
        The lower characteristic tensile strength of concrete (f_ctk_inf) in kN/cm², based on ABNT NBR 6118 - Section 8.2.5.
        """
        result = 0.7 * self.fct_m
        log_property(f"fctk_inf = 0.7 × fct_m = {result:.4f} kN/cm²")
        return result

    @property
    def fctd(self) -> float:
        """
        The design tensile strength of concrete (fctd) in kN/cm², based on ABNT NBR 6118 - Section 12.3.3.
        Considers the lower characteristic tensile strength divided by the safety factor for concrete (gamma_c = 1.4).
        """
        fctk_inf = self.fctk_inf
        result = fctk_inf / GAMMA_C
        log_property(
            f"fctd for {self.name}: fctk_inf/γ_c = {fctk_inf:.4f}/{GAMMA_C} = {result:.4f} kN/cm²"
        )
        return result

    @property
    def alpha_v2(self) -> float:
        """
        The alpha_v2 factor for shear design of concrete, for stirrup calculation with model 1, based on ABNT NBR 6118 - Section 17.4.2.2.
        """
        result = 1.0 - (self.value / 250)
        log_property(
            f"alpha_v2 for {self.name}: 1 - fck/250 = 1 - {self.value}/250 = {result:.4f}"
        )
        return result

    @staticmethod
    def density(reinforced: bool = True) -> float:
        """
        Concrete density in kN/m³, based on ABNT NBR 6118 - Section 8.2.2.
        """
        return 25.0 if reinforced else 24.0
