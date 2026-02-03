class SectionPropertiesCalculator:
    @staticmethod
    def moment_of_inertia(width: int, height: int) -> float:
        """
        Calculate moment of inertia for rectangular section (m, m -> m⁴).
        """
        return (width * height**3) / 12

    @staticmethod
    def cross_sectional_area(width: int, height: int) -> float:
        """
        Calculate cross-sectional area for rectangular section (m, m -> m²).
        """
        return width * height