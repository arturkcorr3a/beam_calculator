"""Carvalho & Figueiredo Filho (2014) - Table 7.2 (Quadro 7.2): Slab deflection coefficients data.

Hardcoded values matching Quadro 7.2 (p. 332) of "Cálculo e Detalhamento de Estruturas Usuais de Concreto Armado".
"""

from src.data.carvalho.table_7_2.model import SlabDeflectionEntry, Table72

# TODO confirm this values one by one
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

# TODO confirm this values one by one
_ENTRIES = (
    SlabDeflectionEntry(1.00, (4.67, 3.20, 3.20, 2.42, 2.21, 2.21, 1.81, 1.81, 1.46)),
    SlabDeflectionEntry(1.05, (5.17, 3.61, 3.42, 2.67, 2.55, 2.31, 2.04, 1.92, 1.60)),
    SlabDeflectionEntry(1.10, (5.64, 4.04, 3.63, 2.91, 2.92, 2.41, 2.27, 2.04, 1.74)),
    SlabDeflectionEntry(1.15, (6.09, 4.47, 3.82, 3.12, 3.29, 2.48, 2.49, 2.14, 1.87)),
    SlabDeflectionEntry(1.20, (6.52, 4.91, 4.02, 3.34, 3.67, 2.56, 2.72, 2.24, 1.98)),
    SlabDeflectionEntry(1.25, (6.95, 5.34, 4.18, 3.55, 4.07, 2.63, 2.95, 2.33, 2.10)),
    SlabDeflectionEntry(1.30, (7.36, 5.77, 4.35, 3.73, 4.48, 2.69, 3.16, 2.42, 2.20)),
    SlabDeflectionEntry(1.35, (7.76, 6.21, 4.50, 3.92, 4.92, 2.72, 3.36, 2.48, 2.30)),
    SlabDeflectionEntry(1.40, (8.14, 6.62, 4.65, 4.08, 5.31, 2.75, 3.56, 2.56, 2.37)),
    SlabDeflectionEntry(1.45, (8.51, 7.02, 4.78, 4.23, 5.73, 2.80, 3.73, 2.62, 2.45)),
    SlabDeflectionEntry(1.50, (8.87, 7.41, 4.92, 4.38, 6.14, 2.84, 3.91, 2.68, 2.51)),
    SlabDeflectionEntry(1.55, (9.22, 7.81, 5.00, 4.53, 6.54, 2.86, 4.07, 2.73, 2.57)),
    SlabDeflectionEntry(1.60, (9.54, 8.17, 5.09, 4.65, 6.93, 2.87, 4.22, 2.78, 2.63)),
    SlabDeflectionEntry(1.65, (9.86, 8.52, 5.13, 4.77, 7.33, 2.87, 4.37, 2.78, 2.68)),
    SlabDeflectionEntry(1.70, (10.15, 8.87, 5.17, 4.88, 7.70, 2.88, 4.51, 2.79, 2.72)),
    SlabDeflectionEntry(1.75, (10.43, 9.19, 5.26, 4.97, 8.06, 2.88, 4.63, 2.81, 2.76)),
    SlabDeflectionEntry(1.80, (10.71, 9.52, 5.36, 5.07, 8.43, 2.89, 4.75, 2.83, 2.80)),
    SlabDeflectionEntry(1.85, (10.96, 9.82, 5.43, 5.16, 8.77, 2.89, 4.87, 2.85, 2.83)),
    SlabDeflectionEntry(1.90, (11.21, 10.11, 5.50, 5.23, 9.08, 2.90, 4.98, 2.87, 2.85)),
    SlabDeflectionEntry(1.95, (11.44, 10.39, 5.58, 5.31, 9.41, 2.90, 5.08, 2.89, 2.88)),
    SlabDeflectionEntry(2.00, (11.68, 10.68, 5.66, 5.39, 9.72, 2.91, 5.19, 2.91, 2.91)),
    SlabDeflectionEntry(
        float("inf"),
        (15.35, 15.35, 6.38, 6.38, 15.35, 3.07, 6.38, 3.07, 3.07),
    ),
)

TABLE_7_2 = Table72(
    title="Table 7.2 - Slab deflection coefficients (Quadro 7.2)",
    reference="Carvalho, R. C.; Figueiredo Filho, J. R. (2014). Cálculo e Detalhamento de Estruturas Usuais de Concreto Armado. 4ª ed. São Carlos: EdUFSCar, p. 332.",
    description=(
        "Dimensionless coefficient alpha used to calculate the elastic deflection "
        "of a solid rectangular reinforced concrete slab according to aspect ratio "
        "(lambda = ly / lx) and support configuration case (1 to 9)."
    ),
    units={
        "aspect_ratio": "dimensionless (ly/lx)",
        "alpha": "dimensionless",
    },
    cases_description=_CASES_DESCRIPTION,
    entries=_ENTRIES,
)

# Backwards compatibility alias
SLAB_DEFLECTION_COEFFICIENTS_TABLE = TABLE_7_2
