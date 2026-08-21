from src.config import APP_CONFIG
from src.data.nbr6120_2019.table_10.data import TABLE_10
from src.data.nbr6120_2019.table_4.data import TABLE_4
from src.data.nbr6120_2019.table_7.data import TABLE_7
from src.data.nbr6120_2019.table_8.data import TABLE_8
from src.properties.concrete import Concrete


class SuperficialLoads:

    @staticmethod
    def get_concrete_element_own_weight(thickness: float, reinforced: bool = True) -> float:
        """
        Calculate the own weight of a superficial concrete element (kN/m²).

        Based on concrete density from ABNT NBR 6120:2019, Table 1.

        Args:
            thickness (float): The thickness of the concrete element in meters.
            reinforced (bool): Whether the concrete is reinforced or not.

        Returns:
            float: The own weight of the concrete element in kN/m².
        """
        concrete_density = Concrete.density(reinforced)

        own_weight = concrete_density * thickness
        return own_weight

    @staticmethod
    def get_infill_weight(material_description: str) -> float:
        """
        Calculate the weight of infill (kN/m²).

        Based on ABNT NBR 6120:2019, Table 7.

        Args:
            material_description (str): The description of the infill material.

        Returns:
            float: The weight of infill in kN/m².
        """
        return TABLE_7.find_material(material_description).weight_avg

    @staticmethod
    def get_ceiling_weight(material_description: str) -> float:
        """
        Calculate the ceiling weight load (kN/m²).

        Based on ABNT NBR 6120:2019, Table 8.

        Args:
            material_description (str): The description of the ceiling material.

        Returns:
            float: The ceiling weight load in kN/m².
        """
        return TABLE_8.find_material(material_description).weight

    @staticmethod
    def get_top_finnish_weight(material_description: str, thickness: float) -> float:
        """
        Calculate the top finnish weight load (kN/m²).

        Based on ABNT NBR 6120:2019, Table 4.

        Args:
            material_description (str): The description of the top finnish material.
            thickness (float): The thickness of the top finnish in cm.

        Returns:
            float: The top finnish weight load in kN/m².
        """
        return TABLE_4.find_material(material_description).get_weight(thickness)

    @staticmethod
    def get_variable_usage_load(local: str) -> float:
        """
        Calculate the variable usage load for a specific location (kN/m²).

        Based on ABNT NBR 6120:2019, Table 10.

        Args:
            local (str): The description of the location.

        Returns:
            float: The variable usage load in kN/m².
        """
        building_category = APP_CONFIG.building_category

        return TABLE_10.find_category(building_category).get_location_load(local)