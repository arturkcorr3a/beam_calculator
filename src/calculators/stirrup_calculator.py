from math import cos, pi, sin

from src.calculators.utils import cotan
from src.config import APP_CONFIG
from src.logger import log_element, log_operation, logger_label
from src.structural_elements.rectangular_beam import RectangularBeam

STIRRUP_ANGLE = (
    pi / 2
)  # 90 degrees, angle of stirrups with respect to beam axis (Model 1 from NBR 6118)

REFERENCE_VIBRATOR_DIAMETER = 45  # mm, based on SINAPI (code 90585)
MIN_SPACING = (
    REFERENCE_VIBRATOR_DIAMETER / 10.0
)  # cm, minimum stirrup spacing to ensure passage of the vibrator - NBR 6118 - Section 18.3.3.2


@logger_label("Stirrup Calculator {id}")
class StirrupCalculator:
    """Calculate required stirrup reinforcement for rectangular beams using Model 1 (NBR 6118 - Section 17.4)."""

    effective_depth: float

    def __init__(self, beam: RectangularBeam, design_shear_force: float, id: str = ""):
        """Initialize with a rectangular beam."""
        self.beam = beam
        self.design_shear_force = design_shear_force
        self.id = id

    def calculate(self, effective_depth: float) -> float:
        """Calculate required stirrup area and spacing for a given design shear force and effective depth."""
        self.effective_depth = effective_depth
        self.verify_compressed_strut_resistance()
        log_element(
            f"Required Asw/s = {self.required_ratio:.4f} cm²/cm, with max spacing = {self.max_spacing:.1f} cm"
        )
        return self.required_ratio  # cm²/cm

    def verify_compressed_strut_resistance(self) -> None:
        """Verify that the design shear force does not exceed the compressed strut resistance (V_Rd2). NBR 6118 - Section 17.4.2.2."""
        if self.design_shear_force > self.compressed_strut_resistance:
            raise ValueError(
                f"Design shear force (V_Sd = {self.design_shear_force:.2f} kN) exceeds compressed strut resistance (V_Rd2 = {self.compressed_strut_resistance:.2f} kN). Design not verified."
            )
        log_operation(
            "Shear force does not exceed the compressed strut resistance (V_Rd2) - OK."
        )

    @property
    def compressed_strut_resistance(self) -> float:
        """Design resistance of compressed concrete strut (V_Rd2) in kN. NBR 6118 - Section 17.4.2.2."""
        alpha_v2 = APP_CONFIG.pavement_concrete.alpha_v2  # dimensionless
        fcd = APP_CONFIG.pavement_concrete.fcd  # kN/cm²
        bw = self.beam.width  # cm
        compressed_strut_resistance = (
            0.27 * alpha_v2 * fcd * bw * self.effective_depth
        )  # kN
        log_operation(
            f"compressed strut resistance V_Rd2 = {compressed_strut_resistance:.2f} kN"
        )
        return compressed_strut_resistance

    @property
    def concrete_contribution(self) -> float:
        """Concrete contribution to shear resistance (V_c = V_c0) in kN. NBR 6118 - Section 17.4.2.2."""
        fctd = APP_CONFIG.pavement_concrete.fctd  # kN/cm²
        bw = self.beam.width  # cm
        concrete_contribution = 0.6 * fctd * bw * self.effective_depth  # kN
        log_operation(
            f"Concrete contribution V_c = V_c0 = {concrete_contribution:.2f} kN"
        )
        return concrete_contribution

    @property
    def required_contribution(self) -> float:
        """Required shear resistance from stirrups (V_sw) in kN. NBR 6118 - Section 17.4.2.2."""
        vc = self.concrete_contribution  # kN
        vsw_required = self.design_shear_force - vc  # kN
        required_contribution = max(vsw_required, 0)
        log_operation(
            f"Required stirrup contribution V_sw = {required_contribution:.2f} kN"
        )
        return required_contribution

    @property
    def required_ratio(self) -> float:
        """Required stirrup reinforcement ratio (A_sw/s) in cm²/cm. NBR 6118 - Section 17.4.2.2."""
        vsw_required = self.required_contribution  # kN
        fywd = self.beam.steel.fywd  # kN/cm²

        asw_s = vsw_required / (
            0.9
            * self.effective_depth
            * fywd
            * (sin(STIRRUP_ANGLE) + cos(STIRRUP_ANGLE))
        )  # cm²/cm
        asw_s_min = self.minimum_ratio  # cm²/cm
        required_ratio = max(asw_s, asw_s_min)
        log_operation(
            f"Required stirrup reinforcement ratio A_sw/s = {required_ratio:.2f} cm²/cm"
        )
        return required_ratio

    @property
    def minimum_ratio(self) -> float:
        """Minimum stirrup reinforcement ratio (A_sw_min/s) in cm²/cm. NBR 6118 - Section 17.4.1.1.1."""
        fct_m = APP_CONFIG.pavement_concrete.fct_m  # kN/cm²
        fywk = self.beam.steel.fywk  # kN/cm²
        bw = self.beam.width  # cm
        minimum_ratio = 0.2 * fct_m / fywk * bw * sin(STIRRUP_ANGLE)  # cm²/cm
        log_operation(
            f"Minimum stirrup reinforcement ratio A_sw_min/s = {minimum_ratio:.2f} cm²/cm"
        )
        return minimum_ratio

    @property
    def max_spacing(self) -> float:
        """Calculate maximum stirrup spacing (s_max) in cm. NBR 6118 - Section 18.3.3.2"""
        if self.design_shear_force <= 0.67 * self.compressed_strut_resistance:
            max_spacing = min(0.6 * self.effective_depth, 30.0)  # cm
        else:
            max_spacing = min(0.3 * self.effective_depth, 30.0)  # cm
        log_operation(f"Maximum stirrup spacing s_max = {max_spacing:.2f} cm")
        return max_spacing

    def calculate_moment_shift(self) -> float:
        """Calculate the moment shift length a_l of the tension force diagram (model I)

        a_l = d [V_Sd / (2 (V_Sd - V_c)) (1 + cotg α) - cotg α], kept within
        0.5 d <= a_l <= d. When |V_Sd| <= V_c the formula does not apply and
        a_l = d.

        Returns:
            Moment shift length a_l (cm).

        References:
            ABNT NBR 6118:2014 — Section 17.4.2.2 c)
        """
        design_shear_force = abs(self.design_shear_force)  # kN
        concrete_contribution = self.concrete_contribution  # kN
        if design_shear_force <= concrete_contribution:
            moment_shift = self.effective_depth
        else:
            moment_shift = self.effective_depth * (
                design_shear_force
                / (2 * (design_shear_force - concrete_contribution))
                * (1 + cotan(STIRRUP_ANGLE))
                - cotan(STIRRUP_ANGLE)
            )
            moment_shift = min(
                max(moment_shift, 0.5 * self.effective_depth), self.effective_depth
            )
        log_operation(f"moment shift length a_l = {moment_shift:.2f} cm")
        return moment_shift
