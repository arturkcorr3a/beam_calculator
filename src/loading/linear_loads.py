from src.data.nbr6120_2019.table_2.data import TABLE_2
from src.properties.concrete import Concrete


class LinearLoads:
    @staticmethod
    def get_concrete_element_own_weight(area: float, reinforced: bool = True) -> float:
        """
        Calculate the own weight of a linear concrete element (kN;m).

        Args:
            area (float): The area of the concrete element in square meters.
            reinforced (bool): Whether the concrete is reinforced or not.

        Returns:
            float: The own weight of the concrete element in kN/m.
        """
        concrete_density = Concrete.density(reinforced)

        own_weight = concrete_density * area
        return own_weight

    @staticmethod
    def get_wall_load(structural: bool, masonry_type: str, nominal_thickness: float, coating_thickness: int, wall_height: float) -> float:
        """Calculate the linear load (kN/m) of a masonry wall on a beam, based on ABNT NBR 6120:2019 - Section 5.4 - Table 2.

        Args:
            structural: True for structural masonry, False for non-bearing.
            masonry_type: Masonry description (e.g. ``"hollow concrete block"``).
            nominal_thickness: Wall thickness in cm.
            coating_thickness: Coating thickness per face (0, 1, or 2 cm).
            wall_height: Wall height in meters.

        Returns:
            Distributed linear wall load in kN/m.
        """
        return TABLE_2.find_masonry_type(masonry_type, structural).get_thickness(nominal_thickness).get_weight(coating_thickness) * wall_height