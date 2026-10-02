"""Round-trip and I/O tests for src/persistency/yaml_io (save_pavement / load_pavement).

The three original round-trip tests from tests/pavement_elements/test_serialization.py
are preserved verbatim and extended with I/O-specific cases.
"""

from __future__ import annotations

from collections.abc import Generator
from pathlib import Path
from typing import Any

import pytest
import yaml

from src.config import APP_CONFIG, AppConfig
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
from src.persistency.schema import BeamDict, PavementDict, PillarDict, SlabDict

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture(autouse=True)
def restore_app_config() -> Generator[None, None, None]:
    """Snapshot and restore APP_CONFIG around every test.

    load_pavement mutates the global APP_CONFIG singleton in place.  Without
    this guard a saved config (e.g. exposure_class=4) would silently bleed
    into the next test in the suite.
    """
    snapshot = {f: getattr(APP_CONFIG, f) for f in AppConfig.__dataclass_fields__}
    yield
    for field, value in snapshot.items():
        setattr(APP_CONFIG, field, value)


# ---------------------------------------------------------------------------
# Module helpers
# ---------------------------------------------------------------------------


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


def _normalize(document: PavementDict) -> PavementDict:
    """Rewrites pillar ids to positional names so two documents that differ only
    by auto-generated ids compare equal.

    Args:
        document: A pavement dict as produced by pavement_to_dict.

    Returns:
        An equivalent dict whose pillar ids (and every reference to them) are
        replaced by their positional index (p0, p1, ...).
    """
    id_map = {p["id"]: f"p{i}" for i, p in enumerate(document["pillars"])}
    return PavementDict(
        pillars=[
            PillarDict(
                id=id_map[p["id"]],
                x=p["x"],
                y=p["y"],
                width=p["width"],
                depth=p["depth"],
            )
            for p in document["pillars"]
        ],
        beams=[
            BeamDict(
                pillar_ids=[id_map[pid] for pid in b["pillar_ids"]],
                reference_pillar_id=id_map[b["reference_pillar_id"]],
                width=b["width"],
                alignment=b["alignment"],
                wall=b["wall"],
            )
            for b in document["beams"]
        ],
        slabs=[
            SlabDict(
                corner_pillar_ids=[id_map[pid] for pid in s["corner_pillar_ids"]],
                local=s["local"],
                permanent_load=s["permanent_load"],
                lowered=s.get("lowered", 0),
            )
            for s in document["slabs"]
        ],
    )


# ---------------------------------------------------------------------------
# Relocated round-trip tests (originally test_pavement_elements/test_serialization.py)
# ---------------------------------------------------------------------------


def test_round_trip_preserves_configuration(tmp_path: Path) -> None:
    original = build_pavement()
    path = tmp_path / "pavement.yaml"

    save_pavement(original, path)
    loaded = load_pavement(path)

    assert len(loaded.pillars) == len(original.pillars)
    assert len(loaded.beams) == len(original.beams)
    assert len(loaded.slabs) == len(original.slabs)
    # Configuration is identical up to auto-generated ids.
    assert _normalize(pavement_to_dict(loaded)) == _normalize(
        pavement_to_dict(original)
    )


def test_loaded_pavement_resolves(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    # resolve() dimensions beams and writes reports relative to the cwd, so run
    # it inside tmp_path to keep the repo clean.
    monkeypatch.chdir(tmp_path)
    save_pavement(build_pavement(), tmp_path / "pavement.yaml")

    loaded = load_pavement(tmp_path / "pavement.yaml")
    loaded.resolve()

    assert all(beam.height > 0 for beam in loaded.beams.values())


def test_unknown_pillar_reference_raises() -> None:
    document: PavementDict = {
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


# ---------------------------------------------------------------------------
# TestSavePavement
# ---------------------------------------------------------------------------


class TestSavePavement:
    """save_pavement writes a YAML file with the expected structure."""

    def test_file_is_created(self, tmp_path: Path) -> None:
        path = tmp_path / "pavement.yaml"
        save_pavement(build_pavement(), path)
        assert path.exists(), "save_pavement should create the output file"

    def test_file_contains_config_section(self, tmp_path: Path) -> None:
        path = tmp_path / "pavement.yaml"
        save_pavement(build_pavement(), path)
        with path.open(encoding="utf-8") as fh:
            data = yaml.safe_load(fh)
        assert "config" in data, "saved YAML should contain a 'config' section"

    def test_config_section_has_all_persisted_fields(self, tmp_path: Path) -> None:
        path = tmp_path / "pavement.yaml"
        save_pavement(build_pavement(), path)
        with path.open(encoding="utf-8") as fh:
            data = yaml.safe_load(fh)
        config = data["config"]
        for key in (
            "aggregate",
            "max_aggregate_size",
            "max_bar_types",
            "max_layers",
            "pavement_concrete",
            "pavement_steel",
            "building_category",
            "exposure_class",
            "ceiling_height",
        ):
            assert key in config, f"config section should contain '{key}'"

    def test_config_section_omits_log_fields(self, tmp_path: Path) -> None:
        path = tmp_path / "pavement.yaml"
        save_pavement(build_pavement(), path)
        with path.open(encoding="utf-8") as fh:
            data = yaml.safe_load(fh)
        assert "log_level" not in data["config"], (
            "log_level must not be written to disk"
        )
        assert "log_output" not in data["config"], (
            "log_output must not be written to disk"
        )

    def test_creates_missing_parent_directories(self, tmp_path: Path) -> None:
        nested = tmp_path / "nested" / "sub" / "pavement.yaml"
        save_pavement(build_pavement(), nested)
        assert nested.exists(), "save_pavement should create missing parent directories"

    def test_top_level_key_order(self, tmp_path: Path) -> None:
        """pillars, beams, slabs appear before config in the document."""
        path = tmp_path / "pavement.yaml"
        save_pavement(build_pavement(), path)
        with path.open(encoding="utf-8") as fh:
            data = yaml.safe_load(fh)
        keys = list(data.keys())
        assert keys.index("pillars") < keys.index("config"), (
            "'pillars' should come before 'config' in the YAML document"
        )
        assert keys.index("beams") < keys.index("config"), (
            "'beams' should come before 'config'"
        )
        assert keys.index("slabs") < keys.index("config"), (
            "'slabs' should come before 'config'"
        )


# ---------------------------------------------------------------------------
# TestLoadPavement
# ---------------------------------------------------------------------------


class TestLoadPavement:
    """load_pavement reads a YAML file and applies the embedded config to APP_CONFIG."""

    def test_applies_config_to_app_config(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Config values written to the file overwrite APP_CONFIG on load."""
        monkeypatch.setattr(APP_CONFIG, "exposure_class", 4)
        path = tmp_path / "pavement.yaml"
        save_pavement(build_pavement(), path)

        # Reset to a different value so we can observe the mutation.
        monkeypatch.setattr(APP_CONFIG, "exposure_class", 2)
        load_pavement(path)

        assert APP_CONFIG.exposure_class == 4, (
            "load_pavement should apply the file's exposure_class to APP_CONFIG"
        )

    def test_file_without_config_section_still_loads(self, tmp_path: Path) -> None:
        """A file without a config key loads successfully without touching APP_CONFIG."""
        p1 = Pillar(x=0, y=0, width=20, depth=25)
        p2 = Pillar(x=500, y=0, width=30, depth=25)
        p3 = Pillar(x=0, y=400, width=20, depth=35)
        p4 = Pillar(x=500, y=400, width=30, depth=35)

        document: dict[str, list[dict[str, Any]]] = {
            "pillars": [
                {"id": p1.id, "x": 0, "y": 0, "width": 20, "depth": 25},
                {"id": p2.id, "x": 500, "y": 0, "width": 30, "depth": 25},
                {"id": p3.id, "x": 0, "y": 400, "width": 20, "depth": 35},
                {"id": p4.id, "x": 500, "y": 400, "width": 30, "depth": 35},
            ],
            "beams": [],
            "slabs": [],
            # no "config" key
        }
        path = tmp_path / "no_config.yaml"
        with path.open("w", encoding="utf-8") as fh:
            yaml.safe_dump(document, fh, sort_keys=False)

        original_exposure = APP_CONFIG.exposure_class
        loaded = load_pavement(path)

        assert len(loaded.pillars) == 4, (
            "all four pillars should load from a file with no config section"
        )
        assert APP_CONFIG.exposure_class == original_exposure, (
            "APP_CONFIG should be unchanged when no config section is present"
        )

    def test_returns_unresolved_pavement(self, tmp_path: Path) -> None:
        """load_pavement returns an unresolved pavement (beam heights are not set)."""
        path = tmp_path / "pavement.yaml"
        save_pavement(build_pavement(), path)
        loaded = load_pavement(path)
        # height starts equal to width (the default before resolve)
        first_beam = next(iter(loaded.beams.values()))
        assert first_beam.height == first_beam.width, (
            "beam height should equal width (unresolved default) immediately after load"
        )

    def test_path_as_string_is_accepted(self, tmp_path: Path) -> None:
        """load_pavement accepts a plain str path as well as a Path."""
        path = tmp_path / "pavement.yaml"
        save_pavement(build_pavement(), path)
        loaded = load_pavement(str(path))
        assert len(loaded.pillars) == 4, "load_pavement should accept a str path"
