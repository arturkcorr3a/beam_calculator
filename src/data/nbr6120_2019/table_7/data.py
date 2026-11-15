"""ABNT NBR 6120:2019 - Section 5.4 - Table 7: Fills data.

Hardcoded values matching the normative table.

The values are transcribed for use in calculations. The standard is
copyrighted by ABNT; consult the original for the complete table and its notes.

References:
    ABNT NBR 6120:2019 — Section 5.4, Table 7
    ASSOCIAÇÃO BRASILEIRA DE NORMAS TÉCNICAS. ABNT NBR 6120: Ações para o
    cálculo de estruturas de edificações. Rio de Janeiro: ABNT, 2019.
"""

from src.data.nbr6120_2019.table_7.model import FillMaterial, Table7

_MATERIALS = (
    FillMaterial(
        description="Construction debris, rubble",
        weight_min=None,
        weight_max=None,
        weight_avg=15.0,
    ),
    FillMaterial(
        description="Autoclaved aerated concrete blocks",
        weight_min=None,
        weight_max=None,
        weight_avg=5.5,
    ),
    FillMaterial(
        description="Expanded clay",
        weight_min=5.0,
        weight_max=7.0,
        weight_avg=6.0,
    ),
    FillMaterial(
        description="Lightweight concrete (with expanded clay)",
        weight_min=17.0,
        weight_max=19.0,
        weight_avg=18.0,
    ),
    FillMaterial(
        description="Soil",
        weight_min=16.0,
        weight_max=20.0,
        weight_avg=18.0,
    ),
    FillMaterial(
        description="High-density expanded polystyrene (EPS)",
        weight_min=None,
        weight_max=None,
        weight_avg=0.3,
    ),
)


TABLE_7 = Table7(
    title="Table 7 - Fills",
    reference="ABNT NBR 6120:2019 — Section 5.4, Table 7",
    description=(
        "Apparent specific weight values for fill materials. When a range is "
        "provided, the average value is given in parentheses."
    ),
    units={
        "apparent_specific_weight": "kN/m³",
    },
    materials=_MATERIALS,
)
