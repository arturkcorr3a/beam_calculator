"""Carvalho & Figueiredo Filho (2014) - Table 7 (Quadro 7.1): Slab bending moment coefficients data.

Hardcoded values matching Quadro 7.1 of "Cálculo e Detalhamento de Estruturas Usuais de Concreto Armado".
"""

from src.data.carvalho.table_7.model import MomentCoefficients, SlabMomentEntry, Table7

_CASES_DESCRIPTION = {
    1: "Four simply supported borders",
    2: "Three borders simply supported, one short border fixed",
    3: "Three borders simply supported, one long border fixed",
    4: "Two borders simply supported, two adjacent borders fixed",
    5: "Two borders simply supported, two opposite short borders fixed",
    6: "Two borders simply supported, two opposite long borders fixed",
    7: "One long border simply supported, three borders fixed",
    8: "One short border simply supported, three borders fixed",
    9: "Four borders fixed",
}

# REVIEW the values one by one
_ENTRIES = (
    SlabMomentEntry(
        1.00,
        (
            MomentCoefficients(4.41, 4.41),
            MomentCoefficients(3.07, 3.94),
            MomentCoefficients(3.94, 3.07),
            MomentCoefficients(2.81, 2.81),
            MomentCoefficients(2.15, 6.99),
            MomentCoefficients(6.99, 2.15),
            MomentCoefficients(2.13, 2.60),
            MomentCoefficients(2.60, 2.13),
            MomentCoefficients(2.11, 2.11),
        ),
    ),
    SlabMomentEntry(
        1.05,
        (
            MomentCoefficients(4.80, 4.45),
            MomentCoefficients(3.42, 3.78),
            MomentCoefficients(4.19, 2.84),
            MomentCoefficients(3.05, 2.81),
            MomentCoefficients(2.47, 7.43),
            MomentCoefficients(7.20, 1.99),
            MomentCoefficients(2.38, 2.66),
            MomentCoefficients(2.78, 2.09),
            MomentCoefficients(2.31, 2.10),
        ),
    ),
    SlabMomentEntry(
        1.10,
        (
            MomentCoefficients(5.18, 4.49),
            MomentCoefficients(3.77, 3.90),
            MomentCoefficients(4.43, 2.76),
            MomentCoefficients(3.30, 2.81),
            MomentCoefficients(2.78, 7.87),
            MomentCoefficients(7.41, 1.89),
            MomentCoefficients(2.63, 2.71),
            MomentCoefficients(2.95, 2.04),
            MomentCoefficients(2.50, 2.09),
        ),
    ),
    SlabMomentEntry(
        1.15,
        (
            MomentCoefficients(5.56, 4.49),
            MomentCoefficients(4.14, 3.97),
            MomentCoefficients(4.64, 2.68),
            MomentCoefficients(3.53, 2.80),
            MomentCoefficients(3.08, 8.26),
            MomentCoefficients(7.56, 1.80),
            MomentCoefficients(2.87, 2.75),
            MomentCoefficients(3.09, 1.98),
            MomentCoefficients(2.73, 2.06),
        ),
    ),
    SlabMomentEntry(
        1.20,
        (
            MomentCoefficients(5.90, 4.48),
            MomentCoefficients(4.51, 4.05),
            MomentCoefficients(4.85, 2.59),
            MomentCoefficients(3.76, 2.79),
            MomentCoefficients(3.38, 8.65),
            MomentCoefficients(7.70, 1.74),
            MomentCoefficients(3.11, 2.78),
            MomentCoefficients(3.23, 1.92),
            MomentCoefficients(2.94, 2.02),
        ),
    ),
    SlabMomentEntry(
        1.25,
        (
            MomentCoefficients(6.27, 4.45),
            MomentCoefficients(4.88, 4.10),
            MomentCoefficients(5.03, 2.51),
            MomentCoefficients(3.96, 2.74),
            MomentCoefficients(3.79, 9.03),
            MomentCoefficients(7.82, 1.67),
            MomentCoefficients(3.43, 2.79),
            MomentCoefficients(3.34, 1.85),
            MomentCoefficients(3.04, 1.97),
        ),
    ),
    SlabMomentEntry(
        1.30,
        (
            MomentCoefficients(6.60, 4.42),
            MomentCoefficients(5.25, 4.15),
            MomentCoefficients(5.20, 2.42),
            MomentCoefficients(4.16, 2.69),
            MomentCoefficients(4.15, 9.33),
            MomentCoefficients(7.93, 1.59),
            MomentCoefficients(3.56, 2.77),
            MomentCoefficients(3.46, 1.78),
            MomentCoefficients(3.13, 1.91),
        ),
    ),
    SlabMomentEntry(
        1.35,
        (
            MomentCoefficients(6.93, 4.37),
            MomentCoefficients(5.60, 4.18),
            MomentCoefficients(5.36, 2.34),
            MomentCoefficients(4.33, 2.65),
            MomentCoefficients(4.50, 9.69),
            MomentCoefficients(8.02, 1.52),
            MomentCoefficients(3.76, 2.74),
            MomentCoefficients(3.55, 1.72),
            MomentCoefficients(3.25, 1.86),
        ),
    ),
    SlabMomentEntry(
        1.40,
        (
            MomentCoefficients(7.25, 4.33),
            MomentCoefficients(5.95, 4.21),
            MomentCoefficients(5.51, 2.25),
            MomentCoefficients(4.51, 2.60),
            MomentCoefficients(4.85, 10.00),
            MomentCoefficients(8.11, 1.45),
            MomentCoefficients(3.96, 2.71),
            MomentCoefficients(3.64, 1.64),
            MomentCoefficients(3.38, 1.81),
        ),
    ),
    SlabMomentEntry(
        1.45,
        (
            MomentCoefficients(7.55, 4.30),
            MomentCoefficients(6.27, 4.19),
            MomentCoefficients(5.64, 2.19),
            MomentCoefficients(4.66, 2.54),
            MomentCoefficients(5.19, 10.25),
            MomentCoefficients(8.13, 1.38),
            MomentCoefficients(4.15, 2.67),
            MomentCoefficients(3.71, 1.59),
            MomentCoefficients(3.48, 1.73),
        ),
    ),
    SlabMomentEntry(
        1.50,
        (
            MomentCoefficients(7.86, 4.25),
            MomentCoefficients(6.60, 4.18),
            MomentCoefficients(5.77, 2.12),
            MomentCoefficients(4.81, 2.47),
            MomentCoefficients(5.53, 10.49),
            MomentCoefficients(8.15, 1.34),
            MomentCoefficients(4.32, 2.63),
            MomentCoefficients(3.78, 1.53),
            MomentCoefficients(3.58, 1.66),
        ),
    ),
    SlabMomentEntry(
        1.55,
        (
            MomentCoefficients(8.12, 4.20),
            MomentCoefficients(6.90, 4.17),
            MomentCoefficients(5.87, 2.04),
            MomentCoefficients(4.93, 2.39),
            MomentCoefficients(5.86, 10.70),
            MomentCoefficients(8.20, 1.28),
            MomentCoefficients(4.48, 2.60),
            MomentCoefficients(3.84, 1.47),
            MomentCoefficients(3.66, 1.60),
        ),
    ),
    SlabMomentEntry(
        1.60,
        (
            MomentCoefficients(
                8.34, 4.14
            ),  # NOTE In the book it was 3.14, but it made no sense, so I changed it to 4.14, which is consistent with the trend of the other values
            MomentCoefficients(7.21, 4.14),
            MomentCoefficients(5.98, 1.95),
            MomentCoefficients(5.06, 2.31),
            MomentCoefficients(6.18, 10.91),
            MomentCoefficients(8.25, 1.23),
            MomentCoefficients(4.63, 2.55),
            MomentCoefficients(3.89, 1.42),
            MomentCoefficients(3.73, 1.54),
        ),
    ),
    SlabMomentEntry(
        1.65,
        (
            MomentCoefficients(8.62, 4.07),
            MomentCoefficients(7.42, 4.12),
            MomentCoefficients(6.07, 1.87),
            MomentCoefficients(5.16, 2.24),
            MomentCoefficients(6.48, 11.08),
            MomentCoefficients(8.28, 1.18),
            MomentCoefficients(4.78, 2.50),
            MomentCoefficients(3.94, 1.37),
            MomentCoefficients(3.80, 1.47),
        ),
    ),
    SlabMomentEntry(
        1.70,
        (
            MomentCoefficients(8.86, 4.00),
            MomentCoefficients(7.62, 4.09),
            MomentCoefficients(6.16, 1.79),
            MomentCoefficients(5.27, 2.16),
            MomentCoefficients(6.81, 11.24),
            MomentCoefficients(8.30, 1.15),
            MomentCoefficients(4.92, 2.45),
            MomentCoefficients(3.98, 1.32),
            MomentCoefficients(3.86, 1.40),
        ),
    ),
    SlabMomentEntry(
        1.75,
        (
            MomentCoefficients(9.06, 3.96),
            MomentCoefficients(7.66, 4.05),
            MomentCoefficients(6.24, 1.74),
            MomentCoefficients(5.36, 2.11),
            MomentCoefficients(7.11, 11.39),
            MomentCoefficients(8.31, 1.11),
            MomentCoefficients(5.04, 2.39),
            MomentCoefficients(4.01, 1.27),
            MomentCoefficients(3.91, 1.36),
        ),
    ),
    SlabMomentEntry(
        1.80,
        (
            MomentCoefficients(9.27, 3.91),
            MomentCoefficients(7.69, 3.99),
            MomentCoefficients(6.31, 1.68),
            MomentCoefficients(5.45, 2.04),
            MomentCoefficients(7.41, 11.43),
            MomentCoefficients(8.32, 1.08),
            MomentCoefficients(5.17, 2.32),
            MomentCoefficients(4.04, 1.20),
            MomentCoefficients(3.95, 1.32),
        ),
    ),
    SlabMomentEntry(
        1.85,
        (
            MomentCoefficients(9.45, 3.83),
            MomentCoefficients(8.22, 3.97),
            MomentCoefficients(6.38, 1.64),
            MomentCoefficients(5.53, 1.99),
            MomentCoefficients(7.68, 11.65),
            MomentCoefficients(8.33, 1.04),
            MomentCoefficients(5.26, 2.27),
            MomentCoefficients(4.07, 1.17),
            MomentCoefficients(3.98, 1.26),
        ),
    ),
    SlabMomentEntry(
        1.90,
        (
            MomentCoefficients(9.63, 3.75),
            MomentCoefficients(8.74, 3.94),
            MomentCoefficients(6.43, 1.59),
            MomentCoefficients(5.60, 1.93),
            MomentCoefficients(7.95, 11.77),
            MomentCoefficients(8.33, 1.01),
            MomentCoefficients(5.36, 2.22),
            MomentCoefficients(4.10, 1.14),
            MomentCoefficients(4.01, 1.21),
        ),
    ),
    SlabMomentEntry(
        1.95,
        (
            MomentCoefficients(9.77, 3.71),
            MomentCoefficients(8.97, 3.88),
            MomentCoefficients(6.47, 1.54),
            MomentCoefficients(5.67, 1.91),
            MomentCoefficients(8.21, 11.83),
            MomentCoefficients(8.33, 0.97),
            MomentCoefficients(5.45, 2.14),
            MomentCoefficients(4.11, 1.11),
            MomentCoefficients(4.04, 1.19),
        ),
    ),
    SlabMomentEntry(
        2.00,
        (
            MomentCoefficients(10.00, 3.64),
            MomentCoefficients(9.18, 3.80),
            MomentCoefficients(6.51, 1.48),
            MomentCoefficients(5.74, 1.88),
            MomentCoefficients(8.47, 11.88),
            MomentCoefficients(8.33, 0.97),
            MomentCoefficients(5.55, 2.07),
            MomentCoefficients(4.13, 1.08),
            MomentCoefficients(4.07, 1.16),
        ),
    ),
    SlabMomentEntry(
        float("inf"),
        (
            MomentCoefficients(12.57, 3.77),
            MomentCoefficients(9.18, 3.80),
            MomentCoefficients(7.61, 1.48),
            MomentCoefficients(7.06, 1.95),
            MomentCoefficients(12.58, 11.88),
            MomentCoefficients(8.33, 0.97),
            MomentCoefficients(7.07, 2.05),
            MomentCoefficients(4.18, 1.09),
            MomentCoefficients(4.19, 1.17),
        ),
    ),
)

TABLE_7 = Table7(
    title="Table 7 - Slab bending moment coefficients (Quadro 7.1)",
    reference="Carvalho, R. C.; Figueiredo Filho, J. R. (2014). Cálculo e Detalhamento de Estruturas Usuais de Concreto Armado. 4ª ed. São Carlos: EdUFSCar.",
    description=(
        "Dimensionless coefficients mu_x and mu_y used to calculate the elastic "
        "bending moments (Mx and My) of a solid rectangular reinforced concrete slab "
        "according to aspect ratio (lambda = ly / lx) and support configuration case (1 to 9)."
    ),
    units={
        "aspect_ratio": "dimensionless (ly/lx)",
        "mu_x": "dimensionless",
        "mu_y": "dimensionless",
    },
    cases_description=_CASES_DESCRIPTION,
    entries=_ENTRIES,
)

# Backwards compatibility alias
SLAB_MOMENT_COEFFICIENTS_TABLE = TABLE_7
