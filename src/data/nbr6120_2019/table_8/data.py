"""ABNT NBR 6120:2019 - Section 5.4 - Table 8: Ceilings, ducts and sprinklers data.

Hardcoded values matching the normative table.
"""

from src.data.nbr6120_2019.table_8.model import CeilingDuctSprinklerMaterial, Table8

_MATERIALS = (
    CeilingDuctSprinklerMaterial(
        description="Mineral fiber ceiling, includes support structure",
        weight=0.10,
    ),
    CeilingDuctSprinklerMaterial(
        description="Drywall ceiling, includes support structure",
        weight=0.25,
    ),
    CeilingDuctSprinklerMaterial(
        description="Plasterboard ceiling, includes support structure",
        weight=0.15,
    ),
    CeilingDuctSprinklerMaterial(
        description="PVC ceiling, includes support structure",
        weight=0.10,
    ),
    CeilingDuctSprinklerMaterial(
        description="Aluminum plate ceiling, includes support structure",
        weight=0.10,
    ),
    CeilingDuctSprinklerMaterial(
        description="Ventilation ducts, without thermal insulation",
        weight=0.20,
    ),
    CeilingDuctSprinklerMaterial(
        description="Air conditioning ducts, with thermal insulation",
        weight=0.30,
    ),
    CeilingDuctSprinklerMaterial(
        description="Automatic sprinkler distribution network with nominal diameter up to 65 mm",
        weight=0.10,
    ),
    CeilingDuctSprinklerMaterial(
        description="Automatic sprinkler distribution network with nominal diameter up to 80 mm",
        weight=0.15,
    ),
)


TABLE_8 = Table8(
    title="Table 8 - Ceilings, ducts and sprinklers",
    reference="ABNT NBR 6120:2019",
    description=(
        "Nominal characteristic values for the self-weight of ceilings, ducts, "
        "and sprinklers."
    ),
    units={
        "weight": "kN/m²",
    },
    materials=_MATERIALS,
)
