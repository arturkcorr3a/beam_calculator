from math import pi, sqrt


class SectionPropertiesCalculator:
    """
    Calculates geometric properties of cross-sections.
    """

    @staticmethod
    def moment_of_inertia(width: float, height: float) -> float:
        """
        Calculates moment of inertia (I) for rectangular section (cm, cm -> cm⁴).
        """
        return (width * height**3) / 12

    @staticmethod
    def rectangular_cross_sectional_area(width: float, height: float) -> float:
        """
        Calculates cross-sectional area (A) for rectangular section (cm, cm -> cm²).
        """
        return width * height

    @staticmethod
    def circular_cross_sectional_area(diameter: float) -> float:
        """
        Calculates cross-sectional area (A) for circular section (cm -> cm²).
        """
        return (pi * (diameter**2)) / 4.0

    @staticmethod
    def gross_section_modulus(width: float, height: float) -> float:
        """
        Calculates the gross section modulus (W_0) for rectangular section (cm, cm -> cm³).
        """
        # CONFIRM if the distance from the neutral axis to the edge is h/2 or y_max (if it's from the real or equivalent neutral axis)
        return (width * height**2) / 6.0

    @staticmethod
    def cracked_section_moment_of_inertia(
        width: float,
        effective_depth: float,
        tension_reinforcement_area: float,
        modular_ratio: float,
        compression_reinforcement_area: float = 0.0,
        compression_distance: float = 0.0,
    ) -> float:
        # FIXME docstring in english
        """
        Calculates the cracked moment of inertia (I_II) for a rectangular section with reinforcement.

        Based on "Cálculo e Detalhamento de Estruturas Usuais de Concreto Armado" (Roberto Chust de Carvalho e Jasson Rodrigues de Figueiredo Filho) - Chapter 4


        Args:
            width : float
                Largura da seção transversal (b) em cm.
            height : float
                Altura total da seção transversal (h) em cm.
            effective_depth : float
                Altura útil da seção (d) em cm.
            tension_reinforcement_area : float
                Área da armadura longitudinal de tração (As) em cm².
            compression_reinforcement_area : float, opcional
                Área da armadura longitudinal de compressão (As') em cm². O padrão é 0.0.
            compression_distance : float, opcional
                Distância da fibra mais comprimida ao CG da armadura de compressão (d') em cm.
                O padrão é 0.0. Deve ser especificada se compression_reinforcement_area > 0.
            modular_ratio : float, opcional
                Razão modular entre o aço e o concreto (alpha_e = Es / Ecs). O padrão é 10.0.

        Retorna:
        --------
        CrackedSectionProperties
            NamedTuple contendo a linha neutra (x_II) em cm e a inércia fissurada (I_II) em cm^4.
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

        return term_concrete + term_tension_steel + term_compression_steel
