"""Round-trip tests for pavement YAML serialization."""

import pytest

from src.loading.superficial_loads import SuperficialLoads
from src.pavement_elements.continuous_beam import ContinuousBeam, WallDefinition
from src.pavement_elements.geometry_utils import Alignment
from src.pavement_elements.pavement import Pavement
from src.pavement_elements.pillar import Pillar
from src.pavement_elements.slab import Slab
from src.persistency import (
    load_pavement,
    pavement_from_dict,
    pavement_to_dict,
    save_pavement,
)


def build_pavement() -> Pavement:
    """Assemble a 4-pillar / 4-beam / 1-slab residential pavement fixture.

    Mirrors the manual single-panel example: four corner pillars with distinct
    sections, an outer-aligned rectangular beam perimeter, and one slab spanning
    the four corners under a residential permanent load (NBR 6120).
    """
    bottom_left = Pillar(x=0, y=0, width=20, depth=25)
    bottom_right = Pillar(x=500, y=0, width=30, depth=25)
    top_left = Pillar(x=0, y=400, width=20, depth=35)
    top_right = Pillar(x=500, y=400, width=30, depth=35)
    pillars = [bottom_left, bottom_right, top_left, top_right]

    pavement = Pavement()
    for pillar in pillars:
        pavement.add_pillar(pillar)

    wall = WallDefinition(
        structural=False,
        masonry_type="hollow concrete block",
        nominal_thickness=14,  # cm
        coating_thickness=1,  # cm per face
    )

    beam_width = 16  # cm
    beam_specs = [
        ([bottom_left.id, bottom_right.id], bottom_left.id, Alignment.BOTTOM),
        ([top_left.id, top_right.id], top_left.id, Alignment.TOP),
        ([bottom_left.id, top_left.id], bottom_left.id, Alignment.LEFT),
        ([bottom_right.id, top_right.id], bottom_right.id, Alignment.RIGHT),
    ]
    for pillar_ids, reference_id, alignment in beam_specs:
        pavement.add_beam(
            ContinuousBeam(
                pillar_ids=pillar_ids,
                reference_pillar_id=reference_id,
                width=beam_width,
                alignment=alignment,
                wall=wall,
            )
        )

    slab = Slab(
        corner_pillar_ids=(
            bottom_left.id,
            bottom_right.id,
            top_left.id,
            top_right.id,
        ),
        local="Bedrooms",
    )
    floor_covering = SuperficialLoads.get_top_finish_weight(
        "Floor coverings of residential", thickness=5.0
    )  # kN/m²
    ceiling = SuperficialLoads.get_ceiling_weight("plaster")  # kN/m²
    self_weight = SuperficialLoads.get_concrete_element_own_weight(
        slab.thickness / 100  # cm -> m
    )  # kN/m²
    slab.add_permanent_load(floor_covering + ceiling + self_weight)

    pavement.add_slab(slab)
    return pavement


def _normalize(document: dict) -> dict:
    """Rewrites pillar ids to positional names so two documents that differ only
    by auto-generated ids compare equal.

    Args:
        document: A pavement dict as produced by pavement_to_dict.

    Returns:
        An equivalent dict whose pillar ids (and every reference to them) are
        replaced by their positional index (p0, p1, ...).
    """
    id_map = {p["id"]: f"p{i}" for i, p in enumerate(document["pillars"])}
    return {
        "pillars": [{**p, "id": id_map[p["id"]]} for p in document["pillars"]],
        "beams": [
            {
                **b,
                "pillar_ids": [id_map[pid] for pid in b["pillar_ids"]],
                "reference_pillar_id": id_map[b["reference_pillar_id"]],
            }
            for b in document["beams"]
        ],
        "slabs": [
            {**s, "corner_pillar_ids": [id_map[pid] for pid in s["corner_pillar_ids"]]}
            for s in document["slabs"]
        ],
    }


def test_round_trip_preserves_configuration(tmp_path):
    original = build_pavement()
    path = tmp_path / "pavement.yaml"

    save_pavement(original, path)
    loaded = load_pavement(path)

    assert len(loaded.pillars) == len(original.pillars)
    assert len(loaded.beams) == len(original.beams)
    assert len(loaded.slabs) == len(original.slabs)
    # Configuration is identical up to auto-generated ids.
    assert _normalize(pavement_to_dict(loaded)) == _normalize(pavement_to_dict(original))


def test_loaded_pavement_resolves(tmp_path, monkeypatch):
    # resolve() dimensions beams and writes reports relative to the cwd, so run
    # it inside tmp_path to keep the repo clean.
    monkeypatch.chdir(tmp_path)
    save_pavement(build_pavement(), tmp_path / "pavement.yaml")

    loaded = load_pavement(tmp_path / "pavement.yaml")
    loaded.resolve()

    assert all(beam.height > 0 for beam in loaded.beams.values())


def test_unknown_pillar_reference_raises():
    document = {
        "pillars": [{"id": "P1", "x": 0, "y": 0, "width": 20, "depth": 25}],
        "beams": [
            {
                "pillar_ids": ["P1", "P99"],
                "reference_pillar_id": "P1",
                "width": 16,
                "alignment": "bottom",
                "wall": {
                    "structural": False,
                    "masonry_type": "hollow concrete block",
                    "nominal_thickness": 14,
                    "coating_thickness": 1,
                },
            }
        ],
        "slabs": [],
    }
    with pytest.raises(ValueError, match="unknown pillar 'P99'"):
        pavement_from_dict(document)
