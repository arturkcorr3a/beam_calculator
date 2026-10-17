"""
Example from "Cálculo e Detalhamento de Estruturas de Concreto Armado'
"""

from src.config import APP_CONFIG
from src.config_options import OccupancyCategory
from src.pavement_elements.continuous_beam import ContinuousBeam, WallDefinition
from src.pavement_elements.geometry_utils import Alignment
from src.pavement_elements.pavement import Pavement
from src.pavement_elements.pillar import Pillar
from src.pavement_elements.slab import Slab
from src.persistency.yaml_io import save_pavement

PATH = "saved/saved.yaml"


def build_pavement():
    pavement = Pavement()

    default_beam_width = 12

    # ADD PILLARS -------

    default_pillar_width = 20
    default_pillar_depth = 18

    horizontally_aligned_pillar_offset = (
        default_pillar_width / 2 - default_beam_width / 2
    )

    p1 = Pillar(
        (0 + horizontally_aligned_pillar_offset),
        1000,
        default_pillar_width,
        default_pillar_depth,
    )
    pavement.add_pillar(p1)

    p2 = Pillar(600, 1000, default_pillar_width, default_pillar_depth)
    pavement.add_pillar(p2)

    p3 = Pillar(
        (1100 - horizontally_aligned_pillar_offset),
        1000,
        default_pillar_width,
        default_pillar_depth,
    )
    pavement.add_pillar(p3)

    p4 = Pillar(
        (0 + horizontally_aligned_pillar_offset),
        400,
        default_pillar_width,
        default_pillar_depth,
    )
    pavement.add_pillar(p4)

    p5 = Pillar(
        (600 - horizontally_aligned_pillar_offset),
        400,
        default_pillar_width,
        default_pillar_depth,
    )
    pavement.add_pillar(p5)

    p6 = Pillar(
        (0 + horizontally_aligned_pillar_offset),
        0,
        default_pillar_width,
        default_pillar_depth,
    )
    pavement.add_pillar(p6)

    p7 = Pillar(
        600,
        0,
        default_pillar_width,
        default_pillar_depth,
    )
    pavement.add_pillar(p7)

    p8 = Pillar(
        (1100 - horizontally_aligned_pillar_offset),
        0,
        default_pillar_width,
        default_pillar_depth,
    )
    pavement.add_pillar(p8)

    # ADD BEAMS -------

    wall = WallDefinition(
        structural=False,
        masonry_type="hollow concrete block",
        nominal_thickness=14,
        coating_thickness=1,
    )

    v1 = ContinuousBeam(
        pillar_ids=[p1.id, p2.id, p3.id],
        reference_pillar_id=p1.id,
        width=default_beam_width,
        alignment=Alignment.CENTER,
        wall=wall,
    )
    pavement.add_beam(v1)

    v2 = ContinuousBeam(
        pillar_ids=[p4.id, p5.id],
        reference_pillar_id=p4.id,
        width=default_beam_width,
        alignment=Alignment.CENTER,
        wall=wall,
    )
    pavement.add_beam(v2)

    v3 = ContinuousBeam(
        pillar_ids=[p6.id, p7.id, p8.id],
        reference_pillar_id=p6.id,
        width=default_beam_width,
        alignment=Alignment.CENTER,
        wall=wall,
    )
    pavement.add_beam(v3)

    v4 = ContinuousBeam(
        pillar_ids=[p6.id, p4.id, p1.id],
        reference_pillar_id=p1.id,
        width=default_beam_width,
        alignment=Alignment.LEFT,
        wall=wall,
    )
    pavement.add_beam(v4)

    v5 = ContinuousBeam(
        pillar_ids=[p7.id, p5.id, p2.id],
        reference_pillar_id=p2.id,
        width=default_beam_width,
        alignment=Alignment.CENTER,
        wall=wall,
    )
    pavement.add_beam(v5)

    v6 = ContinuousBeam(
        pillar_ids=[p8.id, p3.id],
        reference_pillar_id=p3.id,
        width=default_beam_width,
        alignment=Alignment.RIGHT,
        wall=wall,
    )
    pavement.add_beam(v6)

    # ADD SLABS -------

    APP_CONFIG.building_category = OccupancyCategory.COMMERCIAL

    l1 = Slab((p1.id, p2.id, p4.id, p5.id), "General use rooms and bathrooms")
    pavement.add_slab(l1)

    l2 = Slab((p4.id, p5.id, p6.id, p7.id), "General use rooms and bathrooms")
    pavement.add_slab(l2)

    l3 = Slab((p2.id, p3.id, p7.id, p8.id), "General use rooms and bathrooms")
    pavement.add_slab(l3)

    return pavement


def main():
    pavement = build_pavement()
    pavement.resolve()

    for slab in pavement.slabs.values():
        print(f"{slab.id}: {slab.thickness} cm")

    save_pavement(pavement, PATH)


if __name__ == "__main__":
    main()
