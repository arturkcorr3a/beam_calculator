"""ABNT NBR 6120:2019 - Section 5.4 - Table 2: Masonry self-weight data.

Hardcoded values matching the normative table.  Each helper builds one
``MasonryType`` to keep the top-level instantiation readable.
"""

from src.data.nbr6120_2019.table_2.model import MasonryType, Table2, Thickness

# ── Structural masonry ──────────────────────────────────────────────────────

_STRUCTURAL_MASONRY = (
    MasonryType(
        type_description=(
            "Hollow concrete block (Classes A and B - ABNT NBR 6136)"
        ),
        thicknesses=(
            Thickness(14.0, 2.0, 2.3, 2.7),
            Thickness(19.0, 2.7, 3.0, 3.4),
        ),
    ),
    MasonryType(
        type_description=(
            "Hollow ceramic block with solid walls "
            "(Vertical holes - ABNT NBR 15270-1)"
        ),
        thicknesses=(
            Thickness(14.0, 2.0, 2.3, 2.7),
        ),
    ),
    MasonryType(
        type_description=(
            "Hollow ceramic block with hollow walls "
            "(Vertical holes - ABNT NBR 15270-1)"
        ),
        thicknesses=(
            Thickness( 9.0, 1.1, 1.5, 1.9),
            Thickness(11.5, 1.4, 1.8, 2.2),
            Thickness(14.0, 1.7, 2.1, 2.5),
            Thickness(19.0, 2.3, 2.7, 3.1),
        ),
    ),
    MasonryType(
        type_description="Solid ceramic brick (ABNT NBR 15270-1)",
        thicknesses=(
            Thickness( 9.0, 1.6, 2.0, 2.4),
            Thickness(11.5, 2.1, 2.5, 2.9),
            Thickness(14.0, 2.5, 2.9, 3.3),
            Thickness(19.0, 3.4, 3.8, 4.2),
        ),
    ),
    MasonryType(
        type_description=(
            "Hollow calcium silicate block (Class E - ABNT NBR 14974-1)"
        ),
        thicknesses=(
            Thickness( 9.0, 1.1, 1.5, 1.9),
            Thickness(14.0, 1.5, 1.9, 2.3),
            Thickness(19.0, 1.9, 2.3, 2.7),
        ),
    ),
    MasonryType(
        type_description=(
            "Perforated calcium silicate block "
            "(Classes E, F and G - ABNT NBR 14974-1)"
        ),
        thicknesses=(
            Thickness(11.5, 1.9, 2.3, 2.7),
            Thickness(14.0, 2.1, 2.5, 2.9),
            Thickness(17.5, 2.8, 3.2, 3.6),
        ),
    ),
)

# ── Non-bearing masonry ─────────────────────────────────────────────────────

_NON_BEARING_MASONRY = (
    MasonryType(
        type_description="Hollow concrete block (Class C - ABNT NBR 6136)",
        thicknesses=(
            Thickness( 6.5, 1.0, 1.4, 1.8),
            Thickness( 9.0, 1.1, 1.5, 1.9),
            Thickness(11.5, 1.3, 1.7, 2.1),
            Thickness(14.0, 1.4, 1.8, 2.2),
            Thickness(19.0, 1.8, 2.2, 2.6),
        ),
    ),
    MasonryType(
        type_description=(
            "Hollow ceramic block (Horizontal holes - ABNT NBR 15270-1)"
        ),
        thicknesses=(
            Thickness( 9.0, 0.7, 1.1, 1.6),
            Thickness(11.5, 0.9, 1.3, 1.7),
            Thickness(14.0, 1.1, 1.5, 1.9),
            Thickness(19.0, 1.4, 1.8, 2.3),
        ),
    ),
    MasonryType(
        type_description=(
            "Autoclaved aerated concrete block "
            "(Class C25 - ABNT NBR 13438)"
        ),
        thicknesses=(
            Thickness( 7.5, 0.5, 0.9, 1.3),
            Thickness(10.0, 0.6, 1.0, 1.4),
            Thickness(12.5, 0.8, 1.2, 1.6),
            Thickness(15.0, 0.9, 1.3, 1.7),
            Thickness(17.5, 1.1, 1.5, 1.9),
            Thickness(20.0, 1.2, 1.6, 2.0),
        ),
    ),
    MasonryType(
        type_description="Glass block (decorative, non-fire-rated)",
        thicknesses=(
            Thickness(8.0, 0.8, None, None),
        ),
    ),
)

# ── Table 2 singleton ───────────────────────────────────────────────────────

TABLE_2 = Table2(
    title="Table 2 - Masonry",
    reference="ABNT NBR 6120:2019",
    description=(
        "Nominal characteristic values for the self-weight of masonry walls "
        "(structural and non-bearing) based on nominal thickness and coating "
        "thickness per face."
    ),
    units={
        "nominal_thickness": "cm",
        "coating_weight_per_face": "kN/m²",
    },
    structural_masonry=_STRUCTURAL_MASONRY,
    non_bearing_masonry=_NON_BEARING_MASONRY,
    weight_composition_notes=(
        "vertical and horizontal laying mortar made of lime, cement, and sand, with 1 cm thickness and a specific weight of 19 kN/m³;",
        "rendering/plastering with an average specific weight of 19 kN/m³;",
        "proportion of one half-block for every three whole blocks;",
        "no filling of voids (with grout, etc.).",
    ),
)