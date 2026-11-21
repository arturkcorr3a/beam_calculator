"""ABNT NBR 6120:2019 - Section 5.4 - Table 2: Masonry self-weight data.

Hardcoded values matching the normative table.  Each helper builds one
``MasonryType`` to keep the top-level instantiation readable.

The values are transcribed for use in calculations. The standard is
copyrighted by ABNT; consult the original for the complete table and its notes.

References:
    ABNT NBR 6120:2019 — Section 5.4, Table 2
    ASSOCIAÇÃO BRASILEIRA DE NORMAS TÉCNICAS. ABNT NBR 6120: Ações para o
    cálculo de estruturas de edificações. Rio de Janeiro: ABNT, 2019.
"""

from src.data.nbr6120_2019.table_2.model import MasonryType, Table2, Thickness

# ── Masonry (non-bearing / infill) ──────────────────────────────────────────

_MASONRY = (
    MasonryType(
        type_description="Hollow concrete block (Class C - ABNT NBR 6136)",
        thicknesses=(
            Thickness(6.5, 1.0, 1.4, 1.8),
            Thickness(9.0, 1.1, 1.5, 1.9),
            Thickness(11.5, 1.3, 1.7, 2.1),
            Thickness(14.0, 1.4, 1.8, 2.2),
            Thickness(19.0, 1.8, 2.2, 2.6),
        ),
    ),
    MasonryType(
        type_description=("Hollow ceramic block (Horizontal holes - ABNT NBR 15270-1)"),
        thicknesses=(
            Thickness(9.0, 0.7, 1.1, 1.6),
            Thickness(11.5, 0.9, 1.3, 1.7),
            Thickness(14.0, 1.1, 1.5, 1.9),
            Thickness(19.0, 1.4, 1.8, 2.3),
        ),
    ),
    MasonryType(
        type_description=(
            "Autoclaved aerated concrete block (Class C25 - ABNT NBR 13438)"
        ),
        thicknesses=(
            Thickness(7.5, 0.5, 0.9, 1.3),
            Thickness(10.0, 0.6, 1.0, 1.4),
            Thickness(12.5, 0.8, 1.2, 1.6),
            Thickness(15.0, 0.9, 1.3, 1.7),
            Thickness(17.5, 1.1, 1.5, 1.9),
            Thickness(20.0, 1.2, 1.6, 2.0),
        ),
    ),
    MasonryType(
        type_description="Glass block (decorative, non-fire-rated)",
        thicknesses=(Thickness(8.0, 0.8, None, None),),
    ),
)

# ── Table 2 singleton ───────────────────────────────────────────────────────

TABLE_2 = Table2(
    title="Table 2 - Masonry",
    reference="ABNT NBR 6120:2019 — Section 5.4, Table 2",
    description=(
        "Nominal characteristic values for the self-weight of masonry walls "
        "(non-bearing) based on nominal thickness and coating "
        "thickness per face."
    ),
    units={
        "nominal_thickness": "cm",
        "coating_weight_per_face": "kN/m²",
    },
    masonry=_MASONRY,
    weight_composition_notes=(
        "vertical and horizontal laying mortar made of lime, cement, and sand, with 1 cm thickness and a specific weight of 19 kN/m³;",
        "rendering/plastering with an average specific weight of 19 kN/m³;",
        "proportion of one half-block for every three whole blocks;",
        "no filling of voids (with grout, etc.).",
    ),
)
