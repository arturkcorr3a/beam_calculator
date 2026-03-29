from src.beam.rectangular_beam import RectangularBeam
from typing import Tuple
from math import sin, cos, pi

STIRRUP_ANGLE = pi/2  # 90 degrees, angle of stirrups with respect to beam axis (Model 1 from NBR 6118)


class StirrupCalculator:
    """Calculate required stirrup reinforcement for rectangular beams using Model 1 (NBR 6118 - Section 17.4)."""

    def __init__(self, beam: RectangularBeam, effective_depth: float, design_shear_force: float):
        """Initialize with a rectangular beam."""
        self.beam = beam
        self.effective_depth = effective_depth
        self.design_shear_force = design_shear_force

    def calculate(self) -> Tuple[float, float]:
        """Calculate required stirrup area and spacing for a given design shear force and effective depth."""
        self.verify_compressed_strut_resistance()
        return self.required_stirrup_ratio  # cm²/cm
    
    def verify_compressed_strut_resistance(self) -> None:
        """Verify that the design shear force does not exceed the compressed strut resistance (V_Rd2). NBR 6118 - Section 17.4.2.2."""
        if self.design_shear_force <= self.compressed_strut_resistance:
            raise ValueError(f"Design shear force (V_Sd = {self.design_shear_force:.2f} kN) exceeds compressed strut resistance (V_Rd2 = {self.compressed_strut_resistance:.2f} kN). Design not verified.")

    @property
    def compressed_strut_resistance(self) -> float:
        """Design resistance of compressed concrete strut (V_Rd2) in kN. NBR 6118 - Section 17.4.2.2."""
        alpha_v2 = self.beam.concrete.alpha_v2  # dimensionless
        fcd = self.beam.concrete.fcd  # kN/cm²
        bw = self.beam.width  # cm
        return 0.27 * alpha_v2 * fcd * bw * self.effective_depth  # kN

    @property
    def concrete_contribution(self) -> float:
        """Concrete contribution to shear resistance (V_c = V_c0) in kN. NBR 6118 - Section 17.4.2.2."""
        fctd = self.beam.concrete.fctd  # kN/cm²
        bw = self.beam.width  # cm
        return 0.6 * fctd * bw * self.effective_depth  # kN

    @property
    def required_stirrup_contribution(self) -> float:
        """Required shear resistance from stirrups (V_sw) in kN. NBR 6118 - Section 17.4.2.2."""
        vc = self.concrete_contribution  # kN
        
        vsw_required = self.design_shear_force - vc  # kN
        return max(vsw_required, 0)

    @property
    def required_stirrup_ratio(self) -> float:
        """Required stirrup reinforcement ratio (A_sw/s) in cm²/cm. NBR 6118 - Section 17.4.2.2."""
        vsw_required = self.required_stirrup_contribution  # kN
        fywd = self.beam.steel.fywd  # kN/cm²
        asw_s = vsw_required / (0.9 * self.effective_depth * fywd * (sin(STIRRUP_ANGLE) + cos(STIRRUP_ANGLE)))  # cm²/cm
        asw_s_min = self.minimum_stirrup_ratio  # cm²/cm
        return max(asw_s, asw_s_min)

    @property
    def minimum_stirrup_ratio(self) -> float:
        """Minimum stirrup reinforcement ratio (A_sw_min/s) in cm²/cm. NBR 6118 - Section 17.4.1.1.1."""
        fct_m = self.beam.concrete.fct_m  # MPa
        fywk = self.beam.steel.fywk  # kN/cm²
        bw = self.beam.width  # cm
        return 0.2 * fct_m / fywk * bw * sin(STIRRUP_ANGLE)  # cm²/cm

