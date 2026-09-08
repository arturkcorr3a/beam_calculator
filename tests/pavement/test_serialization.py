"""Round-trip tests for pavement YAML serialization."""

import pytest

from src.examples.manual_example_pavement import build_pavement
from src.persistency import (
    load_pavement,
    pavement_from_dict,
    pavement_to_dict,
    save_pavement,
)


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
