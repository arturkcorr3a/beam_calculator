"""Unit tests for src/persistency/deserialization — *_from_dict and all ValueError paths."""

from __future__ import annotations

from typing import cast

import pytest

from src.config import APP_CONFIG, AppConfig
from src.config_options import Aggregate, ExposureClass, OccupancyCategory
from src.errors import MalformedFileError
from src.loading.superficial_loads import SuperficialLoads
from src.pavement_elements.continuous_beam import ContinuousBeam, WallDefinition
from src.pavement_elements.geometry_utils import Alignment
from src.pavement_elements.pavement import Pavement
from src.pavement_elements.pillar import Pillar
from src.pavement_elements.slab import Slab
from src.persistency.deserialization import config_from_dict, pavement_from_dict
from src.persistency.schema import (
    BeamDict,
    ConfigDict,
    PavementDict,
    PillarDict,
    SlabDict,
    WallDict,
)
from src.persistency.serialization import config_to_dict, pavement_to_dict
from src.properties.concrete import Concrete
from src.properties.steel import Steel

# ---------------------------------------------------------------------------
# Module helpers
# ---------------------------------------------------------------------------


def _build_pavement() -> Pavement:
    """Assemble a 4-pillar / 4-beam / 1-slab residential pavement fixture."""
    bottom_left = Pillar(x=0, y=0, width=20, depth=25)
    bottom_right = Pillar(x=500, y=0, width=30, depth=25)
    top_left = Pillar(x=0, y=400, width=20, depth=35)
    top_right = Pillar(x=500, y=400, width=30, depth=35)

    pavement = Pavement()
    for pillar in [bottom_left, bottom_right, top_left, top_right]:
        pavement.add_pillar(pillar)

    wall = WallDefinition(
        masonry_type="hollow concrete block",
        nominal_thickness=14,
        coating_thickness=1,
    )
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
                width=16,
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
    )
    ceiling = SuperficialLoads.get_ceiling_weight("plaster")
    self_weight = SuperficialLoads.get_concrete_element_own_weight(slab.thickness / 100)
    slab.add_permanent_load(floor_covering + ceiling + self_weight)
    pavement.add_slab(slab)
    return pavement


def _normalize(document: PavementDict) -> PavementDict:
    """Rewrites pillar ids to positional names so two documents differing only
    by auto-generated ids compare equal.

    Args:
        document: A pavement dict as produced by pavement_to_dict.

    Returns:
        An equivalent dict whose pillar ids and every reference to them are
        replaced by positional index strings (p0, p1, ...).
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


def _minimal_pillar(pid: str = "P1") -> PillarDict:
    """Build a minimal valid pillar dict."""
    return PillarDict(id=pid, x=0.0, y=0.0, width=20.0, depth=25.0)


def _minimal_wall() -> WallDict:
    """Build a minimal valid wall dict."""
    return WallDict(
        masonry_type="hollow concrete block",
        nominal_thickness=14,
        coating_thickness=1,
    )


def _minimal_beam(p1: str = "P1", p2: str = "P2") -> BeamDict:
    """Build a minimal valid beam dict referencing two pillars."""
    return BeamDict(
        pillar_ids=[p1, p2],
        reference_pillar_id=p1,
        width=16.0,
        alignment="bottom",
        wall=_minimal_wall(),
    )


def _minimal_slab(corners: list[str] | None = None) -> SlabDict:
    """Build a minimal valid slab dict."""
    return SlabDict(
        corner_pillar_ids=corners if corners is not None else ["P1", "P2", "P3", "P4"],
        local="Room",
        permanent_load=3.5,
        lowered=0,
    )


def _minimal_config() -> ConfigDict:
    """Build a minimal valid config dict with all 9 persisted fields."""
    return ConfigDict(
        aggregate="granite",
        max_aggregate_size=2.5,
        max_bar_types=3,
        max_layers=3,
        pavement_concrete="C30",
        pavement_steel="CA50",
        building_category="Residential buildings",
        exposure_class=2,
        ceiling_height=2.5,
    )


# ---------------------------------------------------------------------------
# TestConfigFromDict
# ---------------------------------------------------------------------------


class TestConfigFromDict:
    """config_from_dict round-trips the 9 persisted fields."""

    def test_round_trips_all_persisted_fields(self) -> None:
        serialized = config_to_dict(APP_CONFIG)
        loaded = config_from_dict(serialized)
        assert loaded.aggregate == APP_CONFIG.aggregate, "aggregate should round-trip"
        assert loaded.max_aggregate_size == APP_CONFIG.max_aggregate_size, (
            "max_aggregate_size should round-trip"
        )
        assert loaded.max_bar_types == APP_CONFIG.max_bar_types, (
            "max_bar_types should round-trip"
        )
        assert loaded.max_layers == APP_CONFIG.max_layers, (
            "max_layers should round-trip"
        )
        assert loaded.pavement_concrete == APP_CONFIG.pavement_concrete, (
            "pavement_concrete should round-trip"
        )
        assert loaded.pavement_steel == APP_CONFIG.pavement_steel, (
            "pavement_steel should round-trip"
        )
        assert loaded.building_category == APP_CONFIG.building_category, (
            "building_category should round-trip"
        )
        assert loaded.exposure_class == APP_CONFIG.exposure_class, (
            "exposure_class should round-trip"
        )
        assert loaded.ceiling_height == APP_CONFIG.ceiling_height, (
            "ceiling_height should round-trip"
        )

    def test_log_fields_get_defaults(self) -> None:
        """log_level and log_output are not persisted; they get AppConfig defaults."""
        loaded = config_from_dict(_minimal_config())
        defaults = AppConfig()
        assert loaded.log_level == defaults.log_level, (
            "log_level should revert to the AppConfig default after load"
        )
        assert loaded.log_output == defaults.log_output, (
            "log_output should revert to the AppConfig default after load"
        )

    @pytest.mark.parametrize(
        "missing_key",
        [
            "aggregate",
            "max_aggregate_size",
            "max_bar_types",
            "max_layers",
            "pavement_concrete",
            "pavement_steel",
            "building_category",
            "exposure_class",
            "ceiling_height",
        ],
    )
    def test_missing_key_raises(self, missing_key: str) -> None:
        data: dict[str, object] = dict(_minimal_config())
        del data[missing_key]
        with pytest.raises(
            MalformedFileError, match=f"missing '{missing_key}' in Config"
        ):
            config_from_dict(data)  # type: ignore[arg-type]

    def test_parses_choice_fields_into_enum_members(self) -> None:
        loaded = config_from_dict(_minimal_config())
        assert loaded.aggregate is Aggregate.GRANITE, (
            "aggregate should load as an Aggregate member"
        )
        assert loaded.pavement_concrete is Concrete.C30, (
            "pavement_concrete should load as a Concrete member (by name)"
        )
        assert loaded.pavement_steel is Steel.CA50, (
            "pavement_steel should load as a Steel member (by name)"
        )
        assert loaded.building_category is OccupancyCategory.RESIDENTIAL, (
            "building_category should load as an OccupancyCategory member"
        )
        assert loaded.exposure_class is ExposureClass.MODERATE, (
            "exposure_class should load as an ExposureClass member"
        )

    @pytest.mark.parametrize(
        ("key", "invalid_value"),
        [
            ("aggregate", "unobtainium"),
            ("pavement_concrete", "C31"),
            ("pavement_steel", "CA51"),
            ("building_category", "Spaceports"),
            ("exposure_class", 5),
        ],
    )
    def test_invalid_choice_raises(self, key: str, invalid_value: object) -> None:
        data: dict[str, object] = dict(_minimal_config())
        data[key] = invalid_value
        with pytest.raises(
            MalformedFileError, match=f"invalid {key} '{invalid_value}'"
        ):
            config_from_dict(data)  # type: ignore[arg-type]


# ---------------------------------------------------------------------------
# TestPavementFromDict — happy paths
# ---------------------------------------------------------------------------


class TestPavementFromDict:
    """pavement_from_dict reconstructs an equivalent pavement from a plain dict."""

    def test_pillar_count_preserved(self) -> None:
        original = _build_pavement()
        loaded = pavement_from_dict(pavement_to_dict(original))
        assert len(loaded.pillars) == len(original.pillars), (
            "loaded pavement should have the same number of pillars"
        )

    def test_beam_count_preserved(self) -> None:
        original = _build_pavement()
        loaded = pavement_from_dict(pavement_to_dict(original))
        assert len(loaded.beams) == len(original.beams), (
            "loaded pavement should have the same number of beams"
        )

    def test_slab_count_preserved(self) -> None:
        original = _build_pavement()
        loaded = pavement_from_dict(pavement_to_dict(original))
        assert len(loaded.slabs) == len(original.slabs), (
            "loaded pavement should have the same number of slabs"
        )

    def test_topology_preserved(self) -> None:
        """Pillar ids change on reload but topology (geometry + references) is equal."""
        original = _build_pavement()
        loaded = pavement_from_dict(pavement_to_dict(original))
        assert _normalize(pavement_to_dict(loaded)) == _normalize(
            pavement_to_dict(original)
        ), "normalized topology should be identical after a dict round-trip"

    def test_slab_permanent_load_preserved_before_resolve(self) -> None:
        """permanent_load survives deserialization (it is overwritten later by resolve)."""
        original = _build_pavement()
        original_load = next(iter(original.slabs.values())).permanent_load

        loaded = pavement_from_dict(pavement_to_dict(original))
        loaded_load = next(iter(loaded.slabs.values())).permanent_load

        assert loaded_load == pytest.approx(original_load, abs=1e-5), (  # type: ignore[reportUnknownMemberType]
            "slab permanent_load should be identical right after deserialization"
        )

    def test_slab_lowered_preserved(self) -> None:
        original = _build_pavement()
        next(iter(original.slabs.values())).lowered = 5

        loaded = pavement_from_dict(pavement_to_dict(original))

        assert next(iter(loaded.slabs.values())).lowered == 5, (
            "slab lowered should survive a dict round-trip"
        )

    def test_slab_without_lowered_defaults_to_zero(self) -> None:
        """Files saved before lowered slabs existed load as non-lowered."""
        document = PavementDict(
            pillars=[_minimal_pillar(pid) for pid in ("P1", "P2", "P3", "P4")],
            beams=[],
            slabs=[
                cast(
                    SlabDict,
                    {
                        "corner_pillar_ids": ["P1", "P2", "P3", "P4"],
                        "local": "Room",
                        "permanent_load": 3.5,
                    },
                )
            ],
        )

        loaded = pavement_from_dict(document)

        assert next(iter(loaded.slabs.values())).lowered == 0, (
            "a slab dict without 'lowered' should load with lowered = 0"
        )

    def test_pillar_ids_are_freshly_generated(self) -> None:
        """Loaded pillar ids differ from the saved ids (they are auto-generated)."""
        original = _build_pavement()
        original_ids = set(original.pillars.keys())

        loaded = pavement_from_dict(pavement_to_dict(original))
        loaded_ids = set(loaded.pillars.keys())

        assert loaded_ids != original_ids, (
            "each load should produce freshly generated pillar ids, not copies of the saved ones"
        )

    def test_beam_alignment_reconstructed(self) -> None:
        """Alignment enum is reconstructed correctly from its string value."""
        original = _build_pavement()
        loaded = pavement_from_dict(pavement_to_dict(original))
        alignments = [b.alignment for b in loaded.beams.values()]
        assert Alignment.BOTTOM in alignments, (
            "BOTTOM alignment should survive deserialization"
        )
        assert Alignment.TOP in alignments, (
            "TOP alignment should survive deserialization"
        )


# ---------------------------------------------------------------------------
# TestPavementFromDict — error paths: missing top-level keys
# ---------------------------------------------------------------------------


class TestMissingTopLevelKey:
    """Missing 'pillars', 'beams', or 'slabs' raises a clear ValueError."""

    def test_missing_pillars_key(self) -> None:
        with pytest.raises(MalformedFileError, match="missing 'pillars' in Document"):
            pavement_from_dict({"beams": [], "slabs": []})  # type: ignore[typeddict-item]

    def test_missing_beams_key(self) -> None:
        with pytest.raises(MalformedFileError, match="missing 'beams' in Document"):
            pavement_from_dict({"pillars": [], "slabs": []})  # type: ignore[typeddict-item]

    def test_missing_slabs_key(self) -> None:
        with pytest.raises(MalformedFileError, match="missing 'slabs' in Document"):
            pavement_from_dict({"pillars": [], "beams": []})  # type: ignore[typeddict-item]


# ---------------------------------------------------------------------------
# TestPavementFromDict — error paths: malformed pillar
# ---------------------------------------------------------------------------


class TestMalformedPillar:
    """Missing pillar fields raise descriptive ValueErrors."""

    def test_missing_pillar_id(self) -> None:
        document: PavementDict = {
            "pillars": [{"x": 0.0, "y": 0.0, "width": 20.0, "depth": 25.0}],  # type: ignore[typeddict-item]
            "beams": [],
            "slabs": [],
        }
        with pytest.raises(MalformedFileError, match="missing 'id' in Pillar"):
            pavement_from_dict(document)

    @pytest.mark.parametrize("missing_key", ["x", "y", "width", "depth"])
    def test_missing_geometry_key(self, missing_key: str) -> None:
        pillar: dict[str, object] = dict(_minimal_pillar())
        del pillar[missing_key]
        document: PavementDict = {
            "pillars": [pillar],  # type: ignore[list-item]
            "beams": [],
            "slabs": [],
        }
        with pytest.raises(
            MalformedFileError, match=f"missing '{missing_key}' in Pillar"
        ):
            pavement_from_dict(document)

    def test_pillar_below_min_dimension_raises(self) -> None:
        """Pillar constructors enforce NBR dimension minimums."""
        document: PavementDict = {
            "pillars": [PillarDict(id="P1", x=0.0, y=0.0, width=5.0, depth=25.0)],
            "beams": [],
            "slabs": [],
        }
        with pytest.raises(ValueError):
            pavement_from_dict(document)

    def test_pillar_below_min_area_raises(self) -> None:
        """Pillar area must be at least 360 cm²."""
        # 14 × 14 = 196 cm² < 360 cm²
        document: PavementDict = {
            "pillars": [PillarDict(id="P1", x=0.0, y=0.0, width=14.0, depth=14.0)],
            "beams": [],
            "slabs": [],
        }
        with pytest.raises(ValueError):
            pavement_from_dict(document)


# ---------------------------------------------------------------------------
# TestPavementFromDict — error paths: malformed wall
# ---------------------------------------------------------------------------


class TestMalformedWall:
    """Missing wall fields raise descriptive ValueErrors."""

    @pytest.mark.parametrize(
        "missing_key",
        ["masonry_type", "nominal_thickness", "coating_thickness"],
    )
    def test_missing_wall_key(self, missing_key: str) -> None:
        wall: dict[str, object] = dict(_minimal_wall())
        del wall[missing_key]
        pillar2: PillarDict = PillarDict(
            id="P2", x=500.0, y=0.0, width=20.0, depth=25.0
        )
        beam: dict[str, object] = dict(_minimal_beam("P1", "P2"))
        beam["wall"] = wall
        document: PavementDict = {
            "pillars": [_minimal_pillar("P1"), pillar2],
            "beams": [beam],  # type: ignore[list-item]
            "slabs": [],
        }
        with pytest.raises(
            MalformedFileError, match=f"missing '{missing_key}' in Wall"
        ):
            pavement_from_dict(document)


class TestOptionalWall:
    """A beam may have no wall; the removed 'structural' key is rejected."""

    @staticmethod
    def _document(wall: object) -> PavementDict:
        pillar2 = PillarDict(id="P2", x=500.0, y=0.0, width=20.0, depth=25.0)
        beam: dict[str, object] = dict(_minimal_beam("P1", "P2"))
        beam["wall"] = wall
        return {
            "pillars": [_minimal_pillar("P1"), pillar2],
            "beams": [beam],  # type: ignore[list-item]
            "slabs": [],
        }

    def test_null_wall_loads_as_none(self) -> None:
        pavement = pavement_from_dict(self._document(None))
        assert next(iter(pavement.beams.values())).wall is None, (
            "wall: null should load as a beam without wall"
        )

    def test_structural_key_is_rejected(self) -> None:
        wall = {**_minimal_wall(), "structural": False}
        with pytest.raises(MalformedFileError, match="'structural' in Wall"):
            pavement_from_dict(self._document(wall))


# ---------------------------------------------------------------------------
# TestPavementFromDict — error paths: malformed beam
# ---------------------------------------------------------------------------


class TestMalformedBeam:
    """Missing or invalid beam fields raise descriptive ValueErrors."""

    @pytest.mark.parametrize(
        "missing_key",
        ["wall", "alignment", "pillar_ids", "reference_pillar_id", "width"],
    )
    def test_missing_beam_key(self, missing_key: str) -> None:
        pillar2: PillarDict = PillarDict(
            id="P2", x=500.0, y=0.0, width=20.0, depth=25.0
        )
        beam: dict[str, object] = dict(_minimal_beam("P1", "P2"))
        del beam[missing_key]
        document: PavementDict = {
            "pillars": [_minimal_pillar("P1"), pillar2],
            "beams": [beam],  # type: ignore[list-item]
            "slabs": [],
        }
        with pytest.raises(
            MalformedFileError, match=f"missing '{missing_key}' in Beam"
        ):
            pavement_from_dict(document)

    def test_invalid_alignment_raises(self) -> None:
        pillar2: PillarDict = PillarDict(
            id="P2", x=500.0, y=0.0, width=20.0, depth=25.0
        )
        beam: dict[str, object] = dict(_minimal_beam("P1", "P2"))
        beam["alignment"] = "diagonal"
        document: PavementDict = {
            "pillars": [_minimal_pillar("P1"), pillar2],
            "beams": [beam],  # type: ignore[list-item]
            "slabs": [],
        }
        with pytest.raises(
            MalformedFileError, match="invalid beam alignment 'diagonal'"
        ):
            pavement_from_dict(document)

    def test_unknown_pillar_reference_in_beam_raises(self) -> None:
        document: PavementDict = {
            "pillars": [_minimal_pillar("P1")],
            "beams": [_minimal_beam("P1", "P99")],
            "slabs": [],
        }
        with pytest.raises(MalformedFileError, match="references unknown pillar 'P99'"):
            pavement_from_dict(document)

    def test_beam_with_single_pillar_raises(self) -> None:
        """Beam must reference at least 2 pillars."""
        beam: dict[str, object] = dict(_minimal_beam("P1", "P1"))
        beam["pillar_ids"] = ["P1"]
        document: PavementDict = {
            "pillars": [_minimal_pillar("P1")],
            "beams": [beam],  # type: ignore[list-item]
            "slabs": [],
        }
        with pytest.raises(ValueError):
            pavement_from_dict(document)

    def test_beam_below_min_width_raises(self) -> None:
        """Beam width must be at least 12 cm."""
        pillar2: PillarDict = PillarDict(
            id="P2", x=500.0, y=0.0, width=20.0, depth=25.0
        )
        beam: dict[str, object] = dict(_minimal_beam("P1", "P2"))
        beam["width"] = 10.0
        document: PavementDict = {
            "pillars": [_minimal_pillar("P1"), pillar2],
            "beams": [beam],  # type: ignore[list-item]
            "slabs": [],
        }
        with pytest.raises(ValueError):
            pavement_from_dict(document)


# ---------------------------------------------------------------------------
# TestPavementFromDict — error paths: malformed slab
# ---------------------------------------------------------------------------


class TestMalformedSlab:
    """Missing slab fields or bad pillar references raise descriptive ValueErrors."""

    @pytest.mark.parametrize(
        "missing_key", ["corner_pillar_ids", "local", "permanent_load"]
    )
    def test_missing_slab_key(self, missing_key: str) -> None:
        pillars: list[PillarDict] = [
            _minimal_pillar("P1"),
            PillarDict(id="P2", x=500.0, y=0.0, width=20.0, depth=25.0),
            PillarDict(id="P3", x=0.0, y=400.0, width=20.0, depth=25.0),
            PillarDict(id="P4", x=500.0, y=400.0, width=20.0, depth=25.0),
        ]
        slab: dict[str, object] = dict(_minimal_slab(["P1", "P2", "P3", "P4"]))
        del slab[missing_key]
        document: PavementDict = {
            "pillars": pillars,
            "beams": [],
            "slabs": [slab],  # type: ignore[list-item]
        }
        with pytest.raises(
            MalformedFileError, match=f"missing '{missing_key}' in Slab"
        ):
            pavement_from_dict(document)

    def test_unknown_pillar_reference_in_slab_raises(self) -> None:
        document: PavementDict = {
            "pillars": [_minimal_pillar("P1")],
            "beams": [],
            "slabs": [_minimal_slab(["P1", "P2", "P3", "P4"])],
        }
        with pytest.raises(MalformedFileError, match="references unknown pillar 'P2'"):
            pavement_from_dict(document)

    def test_slab_wrong_corner_count_raises(self) -> None:
        """Slab must have exactly 4 corner pillars."""
        pillars: list[PillarDict] = [
            _minimal_pillar("P1"),
            PillarDict(id="P2", x=500.0, y=0.0, width=20.0, depth=25.0),
            PillarDict(id="P3", x=0.0, y=400.0, width=20.0, depth=25.0),
        ]
        document: PavementDict = {
            "pillars": pillars,
            "beams": [],
            "slabs": [_minimal_slab(["P1", "P2", "P3"])],
        }
        with pytest.raises(ValueError):
            pavement_from_dict(document)
