class SectionPropertiesCalculator:
    """
    Calculates geometric properties of cross-sections.
    """

    @staticmethod
    def moment_of_inertia(width: int, height: int) -> float:
        """
        Calculates moment of inertia (I) for rectangular section (cm, cm -> cm⁴).
        """
        return (width * height**3) / 12

    @staticmethod
    def cross_sectional_area(width: int, height: int) -> float:
        """
        Calculates cross-sectional area (A) for rectangular section (cm, cm -> cm²).
        """
        return width * height
    
    @staticmethod
    def gross_section_modulus(width: int, height: int) -> float:
        """
        Calculates the gross section modulus (W_0) for rectangular section (cm, cm -> cm³).
        """ 
        # CONFIRM se a distância da L.N. até a borda is h/2 or y_max (se é da Linha neutra real ou equivalente)
        return (width * height**2) / 6.0