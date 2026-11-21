from collections.abc import Callable, Sequence
from functools import cached_property
from math import sqrt

from src.calculators.layout_selection import (
    LayerDiameters,
    LayoutPass,
    LayoutSignature,
    select_layout,
)
from src.config import APP_CONFIG
from src.errors import ReinforcementAreaExceededError
from src.loading.forces import (
    design_effort_elu,
    max_design_bending_moment,
    min_design_bending_moment,
)
from src.logger import (
    log_element,
    log_general,
    log_iteration,
    log_operation,
    log_property,
    logger_label,
)
from src.properties.steel import Steel
from src.reinforcement.reinforcement import (
    DEFAULT_STIRRUP_DIAMETER_FOR_D_CALCULATION,
    Reinforcement,
)
from src.structural_elements.rectangular_beam import RectangularBeam

EFFECTIVE_DEPTH_TOLERANCE = 0.01  # cm
MAX_EFFECTIVE_DEPTH_ITERATIONS = 100  # passes before keeping the best layout seen


def _layer_diameters(reinforcement: Reinforcement) -> LayerDiameters:
    """Bar diameters (mm) per layer of a reinforcement"""
    return tuple(
        tuple(bar.diameter_mm for bar in layer.bars)
        for layer in reinforcement.chosen_bars
    )


@logger_label("Rebar Calculator - {id}")
class RebarCalculator:
    """
    Class responsible for calculating the required rebar area for a rectangular beam.
    """

    def __init__(
        self,
        *,  # This forces the use of keyword arguments for clarity
        beam: RectangularBeam,
        bending_moment: float,
        bending_moment_position: float,
        id: str = "",
        d: float | None = None,  # Optional effective depth parameter
        d_compressed: float | None = None,  # Optional effective depth parameter
        moment_zeros: tuple[float, ...] = (),
        support_moments: tuple[float, ...] = (),
        moment_positions: Callable[[float], Sequence[float]] | None = None,
    ):
        """Initialize the RebarCalculator with a rectangular beam and its design bending moment.

        Args:
            beam: Rectangular beam section.
            bending_moment: Characteristic bending moment (kN.m).
            bending_moment_position: Position along the beam's length where the bending moment is applied (cm).
            moment_zeros: Positions along the beam where the bending moment is zero (cm), used for the bars' anchorage.
            support_moments: Characteristic bending moment on each of the beam's supports (kN.m), aligned with ``beam.supports``; used for the support anchorage checks of positive-moment bars.
            moment_positions: Returns the positions along the beam (cm) where the characteristic bending moment equals a given value (kN.m); when given, the tensioned bars are staggered by layer along the moment diagram.
        """
        self.preset_d = d
        self.preset_d_compressed = d_compressed

        self.beam = beam
        self.bending_moment = bending_moment  # kN.m, characteristic, signed
        self.bending_moment_position = bending_moment_position  # cm
        bending_moment_in_kncm = bending_moment * 100
        self.design_bending_moment = abs(design_effort_elu(bending_moment_in_kncm))

        is_bottom_tensioned = bending_moment >= 0
        is_top_tensioned = not is_bottom_tensioned
        is_span_moment = bending_moment > 0
        self.id = id

        self.tensioned_reinforcement = Reinforcement(
            self.beam,
            is_bottom_reinforcement=is_bottom_tensioned,
            center_position=bending_moment_position,
            id=self.id,
            moment_zeros=moment_zeros,
            support_moments=support_moments if is_span_moment else (),
            span_moment=bending_moment if is_span_moment else None,
            section_moment=bending_moment,
            moment_positions=moment_positions,
        )
        self.compressed_reinforcement = Reinforcement(
            self.beam,
            is_bottom_reinforcement=is_top_tensioned,
            center_position=bending_moment_position,
            id=self.id,
            moment_zeros=moment_zeros,
            is_tensioned=False,
        )
        self.stirrup_diameter: float | None = None  # cm, set by calculate_for

    def cleanup(self) -> None:
        """
        Clears all cached properties to reset the internal state.
        This is useful when updating beam or bending moment properties.
        """
        cached_properties = [
            "tensioned_rebar_area",
            "compressed_rebar_area",
            "as1",
            "max_y",
            "d",
            "d_compressed",
            "corrected_sigma_s2",
        ]
        for prop in cached_properties:
            if hasattr(self, prop):
                delattr(self, prop)
                log_property(f"Cleared cached property: {prop}")

    def calculate_for(
        self, stirrup_diameter: float, moment_shift: float, design_shear: float
    ) -> None:
        """Dimension the longitudinal reinforcement for the given stirrups

        Each pass computes the required areas at the current d and chooses bars for them; it converges when the chosen bars give back the d they were chosen with.
        A repeated layout is a cycle; the cheapest layout in it that covers the area required at its own d is kept.
        Has a cap on MAX_EFFECTIVE_DEPTH_ITERATIONS
        passes.

        Args:
            stirrup_diameter: Diameter of the chosen stirrup bars (cm).
            moment_shift: Moment shift length a_l of the stirrups (cm), used
                for the bars' anchorage.
            design_shear: Design shear force V_d of the span (kN), used for the
                anchorage clamps at the extremity supports.
        """
        self.stirrup_diameter = stirrup_diameter

        self.tensioned_reinforcement.moment_shift = moment_shift
        self.compressed_reinforcement.moment_shift = moment_shift
        self.tensioned_reinforcement.stirrup_diameter = stirrup_diameter
        self.compressed_reinforcement.stirrup_diameter = stirrup_diameter
        self.tensioned_reinforcement.design_shear = design_shear
        self.compressed_reinforcement.design_shear = design_shear

        passes: list[LayoutPass] = []
        last_seen: dict[LayoutSignature, int] = {}  # signature -> latest pass index
        for iteration in range(1, MAX_EFFECTIVE_DEPTH_ITERATIONS + 1):
            log_iteration(f"Iteration {iteration} starting...")
            self.cleanup()
            self.calculate_and_set_required_tensioned_rebar_area()
            used_d = self.d  # cm, from the previous pass's bars
            self._share_section_depths()
            self.tensioned_reinforcement.set_required_area(self.tensioned_rebar_area)
            if not self.is_singly_reinforced:
                self.compressed_reinforcement.set_required_area(
                    self.compressed_rebar_area
                )
            layout_pass = self._current_layout_pass()
            self.cleanup()  # d now follows the bars just chosen
            delta_d = abs(self.d - used_d)  # cm
            log_iteration(
                f"Iteration {iteration} summary: d={used_d:.2f} cm | As1={layout_pass.tensioned_required:.3f} cm2 | As2={layout_pass.compressed_required:.3f} cm2 | delta d={delta_d:.3f} cm"
            )
            if delta_d <= EFFECTIVE_DEPTH_TOLERANCE:
                self.calculate_and_set_required_tensioned_rebar_area()
                break

            previous_index = last_seen.get(layout_pass.signature)
            last_seen[layout_pass.signature] = len(passes)
            passes.append(layout_pass)
            if (
                previous_index is not None
            ):  # if it is not the first time we have tried this layout
                self._resolve_cycle(passes[previous_index:-1], layout_pass)
                break
        else:
            self._resolve_non_convergence(passes)
        final_as2 = 0.0 if self.is_singly_reinforced else self.compressed_rebar_area
        log_element(
            f"d={self.d:.2f} cm | As1={self.tensioned_rebar_area:.3f} cm2 | As2={final_as2:.3f} cm2",
        )

    def _resolve_cycle(self, cycle: list[LayoutPass], repeat: LayoutPass) -> None:
        """Keep the best layout of a cycle of passes

        Args:
            cycle: The passes of the cycle, in order.
            repeat: The pass that repeated the cycle's first layout; its
                required areas are those at the last cycle member's own d.
        """
        kept, is_safe = select_layout(
            cycle, (repeat.tensioned_required, repeat.compressed_required)
        )
        self._apply_layout(kept)
        log_element(
            f"Cycle between {' <-> '.join(p.describe() for p in cycle)}; keeping {kept.describe()}"
        )
        if not is_safe:
            log_general(
                f"WARNING: no layout in the cycle covers the area required at its own d; keeping the largest, {kept.describe()}"
            )

    def _resolve_non_convergence(self, passes: list[LayoutPass]) -> None:
        """Keep the best layout seen when d neither converged nor cycled"""
        self.cleanup()
        self.calculate_and_set_required_tensioned_rebar_area()
        kept, is_safe = select_layout(passes, self._current_requirement())
        self._apply_layout(kept)
        shortfall = "" if is_safe else " (below the area required at its own d)"
        log_general(
            f"WARNING: d did not converge within {MAX_EFFECTIVE_DEPTH_ITERATIONS} iterations; keeping {kept.describe()}{shortfall}"
        )

    def _current_requirement(self) -> tuple[float, float]:
        """Tensioned and compressed areas (cm²) required at the current d"""
        compressed = 0.0 if self.is_singly_reinforced else self.compressed_rebar_area
        return self.tensioned_rebar_area, compressed

    def _current_layout_pass(self) -> LayoutPass:
        """Snapshot the bars just chosen and the areas they were chosen for"""
        tensioned_required, compressed_required = self._current_requirement()
        is_doubly = compressed_required > 0
        compressed = self.compressed_reinforcement
        return LayoutPass(
            signature=(
                _layer_diameters(self.tensioned_reinforcement),
                _layer_diameters(compressed) if is_doubly else (),
            ),
            tensioned_required=tensioned_required,
            compressed_required=compressed_required,
            tensioned_provided=self.tensioned_reinforcement.area,
            compressed_provided=compressed.area if is_doubly else 0.0,
        )

    def _apply_layout(self, layout_pass: LayoutPass) -> None:
        """Re-choose the bars of a previous pass and recompute the areas at its d

        The bar choice is deterministic, so choosing for the same required
        areas gives back the same layout.
        """
        self._share_section_depths()
        self.tensioned_reinforcement.set_required_area(layout_pass.tensioned_required)
        if layout_pass.compressed_required > 0:
            self.compressed_reinforcement.set_required_area(
                layout_pass.compressed_required
            )
        self.cleanup()
        self.calculate_and_set_required_tensioned_rebar_area()

    def _share_section_depths(self) -> None:
        """Hand the current d and y (cm) to both reinforcements, for their clamps and support checks

        y is the stress block depth used by ``as1``.
        """
        y = self.actual_y if self.is_singly_reinforced else self.max_y  # cm
        for reinforcement in (
            self.tensioned_reinforcement,
            self.compressed_reinforcement,
        ):
            reinforcement.effective_depth = self.d
            reinforcement.stress_block_depth = y

    def calculate_and_set_required_tensioned_rebar_area(self) -> None:
        """
        Calculate the required rebar area for a rectangular beam, ensuring it falls within the allowable limits.

        Raises:
            ReinforcementAreaExceededError: If the tension plus compression area exceeds the section's maximum.
        """
        self.tensioned_rebar_area = max(
            self.tensioned_rebar_area, self.min_tension_rebar_area
        )
        total_area = self.tensioned_rebar_area + self.compressed_rebar_area
        if total_area > self.max_rebar_area:
            error = ReinforcementAreaExceededError(
                required_area=total_area, max_area=self.max_rebar_area
            )
            log_operation(error.message)
            raise error

    @property
    def min_tension_rebar_area(self) -> float:
        """
        Minimum tension rebar area (cm²), according to ABNT NBR 6118 - Section 17.3.5.2.1
        """
        md_min = min_design_bending_moment(self.beam)  # kN.cm

        calculator = RebarCalculator(
            beam=self.beam,
            bending_moment=0,
            bending_moment_position=0,
            id="Dummy for min tension rebar area calculation",
            d=self.d,
            d_compressed=self.d_compressed,
        )

        calculator.design_bending_moment = md_min
        calculated_min = calculator.as1  # cm^2
        absolute_min = 0.15 / 100 * self.beam.width * self.beam.height
        min_tension_rebar_area = max(calculated_min, absolute_min)
        log_operation(f"Minimum Tension Rebar Area = {min_tension_rebar_area:.4f} cm²")
        return min_tension_rebar_area

    @property
    def total_area(self) -> float:
        """Total chosen steel area, tensioned + compressed (cm²)."""
        return self.tensioned_reinforcement.area + self.compressed_reinforcement.area

    @cached_property
    def max_rebar_area(self) -> float:
        """
        Maximum rebar area (cm²) according to ABNT NBR 6118 - Section 17.3.5.2.4
        """
        max_rebar_area = 0.04 * self.beam.area
        log_property(f"Maximum Rebar Area = {max_rebar_area:.4f} cm²")
        return max_rebar_area

    @property
    def is_singly_reinforced(self) -> bool:
        """
        Determines if the given rectangular beam can be classified as singly reinforced for the provided design bending moment.
        """
        is_singly_reinforced = self.design_bending_moment <= max_design_bending_moment(
            self.beam, self.d, self.max_y
        )
        log_property(f"Is Singly Reinforced = {is_singly_reinforced}")
        return is_singly_reinforced

    @cached_property
    def tensioned_rebar_area(self) -> float:
        """
        Calculates the required tensioned rebar area (cm²), As, for both single and double reinforcement cases.
        """
        tensioned_rebar_area = (
            self.as1
            if self.is_singly_reinforced
            else self.as1 + self.calculate_delta_as()
        )
        log_operation(
            f"Required tensioned rebar area (As) = {tensioned_rebar_area:.4f} cm²"
        )
        return tensioned_rebar_area

    @cached_property
    def compressed_rebar_area(self) -> float:
        """
        Calculates the required compressed rebar area (cm²), As2, for double reinforcement cases, based on the difference between the design bending moment and the maximum bending moment that the beam can resist with single reinforcement, and the current rebar configuration.
        """
        delta_moment = self.calculate_delta_bending_moment()  # kN.cm
        compressed_rebar_area = delta_moment / (
            self.corrected_sigma_s2 * (self.d - self.d_compressed)
        )
        log_operation(
            f"Required compressed rebar area (As2) = {compressed_rebar_area:.4f} cm²"
        )
        return compressed_rebar_area

    @cached_property
    def as1(self) -> float:
        """
        Calculates the required tensioned rebar area (As1) for the current design bending moment, based on the actual depth of the equivalent rectangular stress block (y) and equilibrium of internal forces.
        """
        uniform_stress = APP_CONFIG.pavement_concrete.uniform_stress  # kN/cm²
        bw = self.beam.width  # cm
        y = self.actual_y if self.is_singly_reinforced else self.max_y  # cm
        as1 = (uniform_stress * bw * y) / (self.beam.steel.fyd)
        log_operation(f"Required tensioned rebar area (As1) = {as1:.4f} cm²")
        return as1

    def calculate_delta_as(self) -> float:
        """
        Calculates the additional tensioned rebar area (cm²) required when the beam is not singly reinforced, based on the stress in the compressed reinforcement and the current rebar configuration.
        """
        delta_as = (
            self.compressed_rebar_area * self.corrected_sigma_s2
        ) / self.beam.steel.fyd
        log_operation(f"Additional tensioned rebar area (ΔAs) = {delta_as:.4f} cm²")
        return delta_as

    @cached_property
    def max_y(self) -> float:
        """
        Calculates the maximum depth (cm) of the equivalent rectangular stress block (y) to maintain both the deformation domain 3 and ductility.
        """
        max_y = min(self.calculate_y_limit(), self.calculate_max_y_ductility())
        log_property(f"Maximum depth (y) = {max_y:.4f} cm")
        return max_y

    def calculate_y_limit(self) -> float:
        """
        Calculates the maximum depth (cm) of the equivalent rectangular stress block to maintain the deformation domain 3 (the limit is to turn to 4, as domain 2 would also be ok), based on ABNT NBR 6118 - Section 17.2.2.
        """
        lambda_c = APP_CONFIG.pavement_concrete.lambda_c  # no unit
        epsilon_cu = APP_CONFIG.pavement_concrete.epsilon_cu  # no unit
        steel_elastic_modulus_in_kn_cm2 = (
            Steel.elastic_modulus / 10
        )  # convert MPa to kN/cm²
        fyd = self.beam.steel.fyd  # kN/cm²
        d = self.d  # cm

        y_limit = (
            lambda_c
            * (
                (epsilon_cu * steel_elastic_modulus_in_kn_cm2)
                / (fyd + epsilon_cu * steel_elastic_modulus_in_kn_cm2)
            )
            * d
        )
        log_property(
            f"Maximum depth (y) limit for transition from domain 3 to 4 = {y_limit:.4f} cm"
        )
        return y_limit

    def calculate_max_y_ductility(self) -> float:
        """
        Maximum depth (cm) of the equivalent rectangular stress block (y) to maintain ductility, based on ABNT NBR 6118 - Section 14.6.4.3.
        """
        if APP_CONFIG.pavement_concrete.value <= 50:
            max_y_ductility = 0.45 * APP_CONFIG.pavement_concrete.lambda_c * self.d
        else:
            max_y_ductility = 0.35 * APP_CONFIG.pavement_concrete.lambda_c * self.d
        log_property(f"Maximum depth (y) for ductility = {max_y_ductility:.4f} cm")
        return max_y_ductility

    @cached_property
    def d(self) -> float:
        """
        Calculates the effective depth (cm) of the beam, considering the nominal covering and reinforcements.
        """
        if self.preset_d is not None:
            log_operation(f"Using preset effective depth (d) = {self.preset_d:.2f} cm")
            return self.preset_d

        log_operation("Calculating effective depth (d)...")
        label = f"Effective depth (d) calculation for {self.id}"
        covering = self._effective_covering(
            self.tensioned_reinforcement, "Tensioned", "d", label
        )
        stirrup_diameter = self._stirrup_diameter_for_depth(label)
        d = (
            self.beam.height
            - covering
            - self.tensioned_reinforcement.get_distance_for_d_calculation(label)
            - stirrup_diameter
        )
        log_operation(f"Effective depth (d) = {d:.2f} cm")
        return d

    def _effective_covering(
        self, reinforcement: Reinforcement, kind: str, depth_name: str, label: str
    ) -> float:
        """Return the covering up to the first layer of a reinforcement

        Uses the nominal covering when the reinforcement is not chosen yet;
        otherwise the largest effective covering among the first layer's bars.

        Args:
            reinforcement: Tensioned or compressed reinforcement of the section.
            kind: Reinforcement name for the error message ("Tensioned" or
                "Compressed").
            depth_name: Depth being calculated, for the error message ("d" or
                "d'").
            label: Logger label of the calling depth calculation.

        Returns:
            Effective covering (cm).

        Raises:
            ValueError: If the reinforcement is chosen but its first layer has
                no bars.
        """
        if not reinforcement.is_chosen:
            return RectangularBeam.nominal_covering  # cm

        first_layer = reinforcement.chosen_bars[0]
        if not first_layer.bars:
            raise ValueError(
                f"{kind} reinforcement is marked chosen, but no bars have been set in the first layer. Cannot calculate effective depth ({depth_name})."
            )
        covering = reinforcement.effective_covering()  # cm
        log_property(
            f"ACTUAL effective covering (c) = {covering:.2f} cm for first layer {first_layer.get_bar_diameters_for_print()}",
            label,
        )
        return covering

    def _stirrup_diameter_for_depth(self, label: str) -> float:
        """Return the stirrup diameter used in the effective depth calculations

        Falls back to DEFAULT_STIRRUP_DIAMETER_FOR_D_CALCULATION while the
        stirrups are not chosen yet.

        Args:
            label: Logger label of the calling depth calculation.

        Returns:
            Stirrup diameter (cm).
        """
        if self.stirrup_diameter is not None:
            log_property(
                f"ACTUAL stirrup diameter (phi) = {self.stirrup_diameter:.2f} cm",
                label,
            )
            return self.stirrup_diameter
        log_property(
            f"Stirrup diameter not chosen, using default for d calculation = {DEFAULT_STIRRUP_DIAMETER_FOR_D_CALCULATION:.2f} cm",
            label,
        )
        return DEFAULT_STIRRUP_DIAMETER_FOR_D_CALCULATION

    @property
    def max_bending_moment(self) -> float:
        """
        Calculates the maximum bending moment (kN.cm) that the beam can resist with single reinforcement, for the current rebar configuration (due to effective depth and maximum y)
        """
        uniform_stress = APP_CONFIG.pavement_concrete.uniform_stress  # kN/cm²
        bw = self.beam.width  # cm
        y_max = self.max_y  # cm
        d = self.d  # cm
        max_bending_moment = uniform_stress * bw * y_max * (d - y_max * 0.5)  # kN.cm
        log_property(
            f"Maximum bending moment for single reinforcement (Md_max) = {max_bending_moment:.2f} kN.cm"
        )
        return max_bending_moment

    @property
    def actual_y(self) -> float:
        """
        Calculates the actual depth of the equivalent rectangular stress block (y) (cm) for the current effective depth and design bending moment. Based on equilibrium of internal forces and moment.
        """
        d = self.d  # cm
        uniform_stress = APP_CONFIG.pavement_concrete.uniform_stress  # kN/cm²
        bw = self.beam.width  # cm
        actual_y = d - sqrt(
            d**2 - (2 * self.design_bending_moment) / (uniform_stress * bw)
        )
        log_operation(
            f"Actual depth of the equivalent rectangular stress block (y) = {actual_y:.2f} cm"
        )
        return actual_y

    def calculate_epsilon_s2(self) -> float:
        """
        Calculates the strain in the compressed reinforcement (no unit) for the current rebar configuration, based on the actual depth of the equivalent rectangular stress block (y), the distance from the extreme compression fiber to the centroid of the compressed rebar (d'), and the maximum depth of the equivalent rectangular stress block (y).
        """
        epsilon_cu = APP_CONFIG.pavement_concrete.epsilon_cu  # no unit
        lambda_c = APP_CONFIG.pavement_concrete.lambda_c  # no unit
        epsilon_s2 = (
            epsilon_cu * (self.max_y - lambda_c * self.d_compressed) / self.max_y
        )
        log_operation(
            f"Strain in the compressed reinforcement (epsilon_s2) = {epsilon_s2:.6f}"
        )
        return epsilon_s2

    @cached_property
    def d_compressed(self) -> float:
        """
        Calculates the distance (cm) from the extreme compression fiber to the centroid of the compressed rebar (d'), considering the current rebar configuration.
        """
        if self.preset_d_compressed is not None:
            log_operation(
                f"Using preset compressed effective depth (d') = {self.preset_d_compressed:.2f} cm"
            )
            return self.preset_d_compressed

        log_operation("Calculating compressed effective depth (d')...")
        label = f"Compressed effective depth (d') calculation for {self.id}"
        covering = self._effective_covering(
            self.compressed_reinforcement, "Compressed", "d'", label
        )
        stirrup_diameter = self._stirrup_diameter_for_depth(label)

        d_compressed = (
            covering
            + stirrup_diameter
            + self.compressed_reinforcement.get_distance_for_d_calculation(label)
        )
        log_operation(f"d' = {d_compressed:.2f} cm")
        return d_compressed

    def calculate_sigma_s2(self) -> float:
        """
        Calculates the stress in the compressed reinforcement (kN/cm²) for the current rebar configuration, based on the calculated strain and the steel elastic modulus, ensuring it does not exceed the maximum stress allowed for the steel (fyd).
        """
        steel_elastic_modulus_in_kn_cm2 = (
            Steel.elastic_modulus / 10
        )  # convert MPa to kN/cm²
        calculated_sigma_s2 = (
            self.calculate_epsilon_s2() * steel_elastic_modulus_in_kn_cm2
        )  # kN/cm²
        max_sigma_s2 = self.beam.steel.fyd  # kN/cm²
        sigma_s2 = min(calculated_sigma_s2, max_sigma_s2)
        log_operation(
            f"Stress in the compressed reinforcement (sigma_s2) = {sigma_s2:.2f} kN/cm²"
        )
        return sigma_s2

    @cached_property
    def corrected_sigma_s2(self) -> float:
        """
        Calculates the corrected stress in the compressed reinforcement (kN/cm²), accounting for the area occupied by the reinforcement in the concrete compression zone.

        This correction ensures that the compressed reinforcement properly accounts for the stress contribution without affecting the calculation of the additional tensioned reinforcement.
        """
        sigma_s2 = self.calculate_sigma_s2()  # kN/cm²
        corrected_sigma_s2 = sigma_s2 - APP_CONFIG.pavement_concrete.uniform_stress
        log_operation(
            f"Corrected stress in the compressed reinforcement (corrected_sigma_s2) = {corrected_sigma_s2:.2f} kN/cm²"
        )
        return corrected_sigma_s2

    def calculate_delta_bending_moment(self) -> float:
        """
        Calculates the difference (kN.cm) between the design bending moment and the maximum bending moment that the beam can resist with single reinforcement, for the current rebar configuration. This difference is used to determine the required compressed reinforcement area when the beam is not singly reinforced.
        """
        delta_bending_moment = self.design_bending_moment - self.max_bending_moment
        log_property(f"Delta bending moment = {delta_bending_moment:.2f} kN.cm")
        return delta_bending_moment
