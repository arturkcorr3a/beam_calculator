"""ABNT NBR 6120:2019 - Section 5.4 - Table 4: Floor coverings and waterproofing data.

Hardcoded values matching the normative table.
"""

from src.data.nbr6120_2019.table_4.model import (
    CoveringMaterial,
    Table4,
    ThicknessWeight,
)

_MATERIALS = (
    CoveringMaterial(
        description=(
            "Simple asphalt felt waterproofing (only felt with 15 percent overlap and "
            "asphalt paint, without leveling layer or mechanical protection)"
        ),
        thicknesses=(
            ThicknessWeight(0.3, 0.08),
            ThicknessWeight(0.4, 0.10),
            ThicknessWeight(0.5, 0.11),
        ),
    ),
    CoveringMaterial(
        description=(
            "Internal raised floor with steel plates, without coating "
            "(up to 30 cm height)"
        ),
        thicknesses=(
            ThicknessWeight(None, 0.5),
        ),
    ),
    CoveringMaterial(
        description=(
            "Internal raised floor with polypropylene plates, without coating "
            "(up to 30 cm height)"
        ),
        thicknesses=(
            ThicknessWeight(None, 0.15),
        ),
    ),
    CoveringMaterial(
        description=(
            "Floor coverings of residential and commercial buildings "
            "(gamma_{ap-m} = 20 kN/m³)"
        ),
        thicknesses=(
            ThicknessWeight(5.0, 1.0),
            ThicknessWeight(7.0, 1.4),
        ),
    ),
    CoveringMaterial(
        description=(
            "Floor coverings of industrial buildings "
            "(gamma_{ap-m} = 34 kN/m³)"
        ),
        thicknesses=(
            ThicknessWeight(5.0, 1.7),
            ThicknessWeight(7.0, 2.4),
        ),
    ),
    CoveringMaterial(
        description=(
            "Roof waterproofing with asphalt felt and mechanical protection, "
            "without coating (gamma_{ap-m} = 18 kN/m³)"
        ),
        thicknesses=(
            ThicknessWeight(10.0, 1.8),
            ThicknessWeight(15.0, 2.7),
        ),
    ),
)


TABLE_4 = Table4(
    title="Table 4 - Floor coverings and waterproofing",
    reference="ABNT NBR 6120:2019",
    description=(
        "Nominal characteristic values for the self-weight of floor coverings "
        "and waterproofing based on material and thickness."
    ),
    units={
        "thickness": "cm",
        "weight": "kN/m²",
    },
    materials=_MATERIALS,
    notes=(
        "Calculate case by case, considering the thickness of the floor covering components and their respective specific weights. In the absence of more precise information, the indicated average specific weights may be considered.",
    ),
)
