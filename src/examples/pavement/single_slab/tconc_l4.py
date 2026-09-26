"""Isolated pre-sizing test for slab L4 from the t_concreto2 pavement.

L3, L5 and L9 are fixed at h = 8 cm so that L4's edge support conditions are
set before the checker runs.
"""

from src.config import APP_CONFIG
from src.logger import LogLevel, LogOutput, configure_logger
from src.pavement_elements.continuous_beam import ContinuousBeam, WallDefinition
from src.pavement_elements.geometry_utils import Alignment
from src.pavement_elements.pavement import Pavement
from src.pavement_elements.pillar import Pillar
from src.pavement_elements.slab import PermanentLoadDefinition, Slab

FIXED_NEIGHBOR_THICKNESS = 8  # cm


def main() -> None:
    APP_CONFIG.building_category = "Residential buildings"
    APP_CONFIG.ceiling_height = 2.72
    APP_CONFIG.exposure_class = 2
    APP_CONFIG.pavement_concrete = "C40"
    APP_CONFIG.pavement_steel = "CA50"
    APP_CONFIG.aggregate = "granite"

    configure_logger(LogLevel.DISABLED, LogOutput.CONSOLE)
    pavement = Pavement()

    # --- Pillars (full set from t_concreto2, needed for beam/slab resolution) ---
    p1 = Pillar(0.0, 1013.0, 19, 19)
    p2 = Pillar(621.5, (1013.0 - 35 + 9.5), 14, 70)
    p3 = Pillar(1241.5, 1013.0, 50, 19)
    p4 = Pillar(2023.0, (1013.0 - 25 + 9.5), 19, 50)
    p5 = Pillar(0.0, 520.5, 19, 50)
    p6 = Pillar(621.5, 520.5, 14, 70)
    p7 = Pillar(1241.5, 520.5, 14, 70)
    p8 = Pillar(1629.5, (520.5 - 35 + 7), 14, 70)
    p9 = Pillar(1851.5, (520.5 - 15 + 7), 14, 30)
    p10 = Pillar((2023.0 + 9.5 - 15), 520.5, 30, 14)
    p11 = Pillar((0.0 - 9.5 + 15), 301.5, 30, 14)
    p12 = Pillar(621.5, 301.5, 20, 70)
    p13 = Pillar(1241.5, 301.5, 70, 14)
    p14 = Pillar(1629.5, 301.5, 14, 30)
    p15 = Pillar(1851.5, 301.5, 14, 30)
    p16 = Pillar(0.0, 0.0, 19, 19)
    p17 = Pillar(621.5, (0.0 - 9.5 + 30 / 2.0), 19, 30)
    p18 = Pillar(1241.5, (0.0 - 9.5 + 15), 14, 30)
    p19 = Pillar(1629.5, (0.0 - 9.5 + 15), 14, 30)
    p20 = Pillar(1851.5, (0.0 - 9.5 + 15), 14, 30)
    p21 = Pillar(2023.0, 0.0, 19, 19)
    pillars = [
        p1,
        p2,
        p3,
        p4,
        p5,
        p6,
        p7,
        p8,
        p9,
        p10,
        p11,
        p12,
        p13,
        p14,
        p15,
        p16,
        p17,
        p18,
        p19,
        p20,
        p21,
    ]

    wall_14 = WallDefinition(False, "Hollow ceramic block", 14, 1)
    wall_19 = WallDefinition(False, "Hollow ceramic block", 19, 1)

    v1 = ContinuousBeam([p1.id, p2.id, p3.id, p4.id], p1.id, 19, Alignment.TOP, wall_19)
    v2 = ContinuousBeam(
        [p7.id, p8.id, p9.id, p10.id], p7.id, 14, Alignment.CENTER, wall_14
    )
    v3 = ContinuousBeam(
        [p11.id, p12.id, p13.id, p14.id, p15.id], p11.id, 14, Alignment.CENTER, wall_14
    )
    v4 = ContinuousBeam(
        [p16.id, p17.id, p18.id, p19.id, p20.id, p21.id],
        p16.id,
        19,
        Alignment.BOTTOM,
        wall_19,
    )
    v5 = ContinuousBeam(
        [p16.id, p11.id, p5.id, p1.id], p16.id, 19, Alignment.LEFT, wall_19
    )
    v6 = ContinuousBeam(
        [p17.id, p12.id, p6.id, p2.id], p17.id, 14, Alignment.CENTER, wall_14
    )
    v7 = ContinuousBeam(
        [p18.id, p13.id, p7.id, p3.id], p18.id, 14, Alignment.CENTER, wall_14
    )
    v8 = ContinuousBeam([p19.id, p14.id, p8.id], p19.id, 14, Alignment.CENTER, wall_14)
    v9 = ContinuousBeam([p20.id, p15.id, p9.id], p20.id, 14, Alignment.CENTER, wall_14)
    v10 = ContinuousBeam([p21.id, p10.id, p4.id], p21.id, 19, Alignment.RIGHT, wall_19)
    beams = [v1, v2, v3, v4, v5, v6, v7, v8, v9, v10]

    top_finish = PermanentLoadDefinition(
        "Floor coverings of residential and commercial buildings", 5.0
    )
    ceiling_finish = "Ventilation ducts, without thermal insulation"

    Slab(("", "", "", ""), "")  # dummy L1
    l2 = Slab((p1.id, p2.id, p11.id, p12.id), "Bedrooms", top_finish, ceiling_finish)
    l3 = Slab(
        (p2.id, p3.id, p12.id, p13.id),
        "Pantry, service area, and laundry",
        top_finish,
        ceiling_finish,
    )
    l4 = Slab(
        (p3.id, p4.id, p7.id, p10.id),
        "Living rooms, pantries, and kitchens",
        top_finish,
        ceiling_finish,
    )
    l5 = Slab((p7.id, p8.id, p13.id, p14.id), "Bathrooms", top_finish, ceiling_finish)
    l6 = Slab((p11.id, p12.id, p16.id, p17.id), "Bathrooms", top_finish, ceiling_finish)
    l7 = Slab((p12.id, p13.id, p17.id, p18.id), "Bedrooms", top_finish, ceiling_finish)
    l8 = Slab(
        (p14.id, p15.id, p19.id, p20.id),
        "Common use corridors",
        top_finish,
        ceiling_finish,
    )
    l9 = Slab(
        (p9.id, p10.id, p20.id, p21.id),
        "Common use corridors",
        top_finish,
        ceiling_finish,
    )
    slabs = [l2, l3, l4, l5, l6, l7, l8, l9]

    for pillar in pillars:
        pavement.add_pillar(pillar)
    for beam in beams:
        pavement.add_beam(beam)
    for slab in slabs:
        pavement.add_slab(slab)

    # Validate structure (resolves beams, slabs, loads — no pre-sizing yet)
    pavement.validate()
    pavement.pre_size_beams()
    pavement.load_beam_spans()

    # Fix neighbor thicknesses before pre-sizing L4
    l3.thickness = FIXED_NEIGHBOR_THICKNESS
    l5.thickness = FIXED_NEIGHBOR_THICKNESS
    l9.thickness = FIXED_NEIGHBOR_THICKNESS

    configure_logger(LogLevel.PROPERTY, LogOutput.CONSOLE)

    print(
        f"\n--- Pre-sizing L4 (neighbors: L3={l3.thickness} cm, L5={l5.thickness} cm, L9={l9.thickness} cm) ---"
    )
    l4.pre_size()
    print(f"\nResult: L4 thickness = {l4.thickness} cm")


if __name__ == "__main__":
    main()
