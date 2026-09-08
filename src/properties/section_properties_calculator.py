from math import pi, sqrt

from src.logger import log_property, logger_label


@logger_label("Section")
class SectionPropertiesCalculator:
    """
    Calculates geometric properties of cross-sections.
    """

    @staticmethod
    def moment_of_inertia(width: float, height: float) -> float:
        """
        Calculates moment of inertia (I) for rectangular section (cm, cm -> cm⁴).
        """
        result = (width * height**3) / 12
        log_property(f"{width} x {height}: I = {result:.4f} cm⁴")
        return result

    @staticmethod
    def rectangular_cross_sectional_area(width: float, height: float) -> float:
        """
        Calculates cross-sectional area (A) for rectangular section (cm, cm -> cm²).
        """
        result = width * height
        log_property(f"{width} x {height}: A = {result:.4f} cm²")
        return result

    @staticmethod
    def circular_cross_sectional_area(diameter: float) -> float:
        """
        Calculates cross-sectional area (A) for circular section (cm -> cm²).
        """
        result = (pi * (diameter**2)) / 4.0
        log_property(f"D = {diameter} cm: A =  {result:.4f} cm²")
        return result

    @staticmethod
    def gross_section_modulus(width: float, height: float) -> float:
        """
        Calculates the gross section modulus (W_0) for rectangular section (cm, cm -> cm³).
        """
        result = (width * height**2) / 6.0
        log_property(f"{width} x {height}: W_0 = {result:.4f} cm³")
        return result

    @staticmethod
    def cracked_section_moment_of_inertia(
        width: float,
        effective_depth: float,
        tension_reinforcement_area: float,
        modular_ratio: float,
        compression_reinforcement_area: float = 0.0,
        compression_distance: float = 0.0,
    ) -> float:
        """Calculate the cracked moment of inertia (I_II) for a rectangular section with reinforcement.

        Based on "Cálculo e Detalhamento de Estruturas Usuais de Concreto Armado"
        (Roberto Chust de Carvalho e Jasson Rodrigues de Figueiredo Filho) — Chapter 4.

        Args:
            width: Width of the cross-section b (cm).
            effective_depth: Effective depth d (cm).
            tension_reinforcement_area: Longitudinal tension reinforcement area As (cm²).
            modular_ratio: Modular ratio alpha_e = Es / Ecs.
            compression_reinforcement_area: Longitudinal compression reinforcement area As' (cm²).
            compression_distance: Distance from the most compressed fiber to the centroid of the
                compression reinforcement d' (cm). Required when compression_reinforcement_area > 0.

        Returns:
            Cracked moment of inertia I_II (cm⁴).
        """
        a1 = width / 2.0
        a2 = (modular_ratio * tension_reinforcement_area) + (
            (modular_ratio - 1.0) * compression_reinforcement_area
        )
        a3 = -(modular_ratio * tension_reinforcement_area * effective_depth) - (
            (modular_ratio - 1.0)
            * compression_reinforcement_area
            * compression_distance
        )

        discriminant = (a2**2) - (4.0 * a1 * a3)
        if discriminant < 0:
            raise ArithmeticError(
                "Calculation error: The discriminant of the neutral axis equation is negative."
            )
        neutral_axis_depth = (-a2 + sqrt(discriminant)) / (2.0 * a1)  # x_II

        term_concrete = (width * (neutral_axis_depth**3)) / 3.0
        term_tension_steel = (
            modular_ratio
            * tension_reinforcement_area
            * ((effective_depth - neutral_axis_depth) ** 2)
        )
        term_compression_steel = (
            (modular_ratio - 1.0)
            * compression_reinforcement_area
            * ((neutral_axis_depth - compression_distance) ** 2)
        )

        i_ii = term_concrete + term_tension_steel + term_compression_steel
        log_property(f"I_II = {i_ii:.4f} cm⁴ (x_II = {neutral_axis_depth:.4f} cm)")
        return i_ii
