"""Unit tests for src/persistency/serialization — pure *_to_dict output."""

from __future__ import annotations

from src.config import APP_CONFIG, AppConfig
from src.loading.superficial_loads import SuperficialLoads
from src.pavement_elements.continuous_beam import ContinuousBeam, WallDefinition
from src.pavement_elements.geometry_utils import Alignment
from src.pavement_elements.pavement import Pavement
from src.pavement_elements.pillar import Pillar
from src.pavement_elements.slab import Slab
from src.persistency.serialization import config_to_dict, pavement_to_dict

# ---------------------------------------------------------------------------
# Module helpers
# ---------------------------------------------------------------------------


def _build_pavement() -> Pavement:
    """Assemble a 4-pillar / 4-beam / 1-slab residential pavement fixture.

    Mirrors the manual single-panel example: four corner pillars with distinct
    sections, an outer-aligned rectangular beam perimeter, and one slab
    spanning the four corners under a residential permanent load.
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
        nominal_thickness=14,
        coating_thickness=1,
    )

    beam_width = 16
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
    )
    ceiling = SuperficialLoads.get_ceiling_weight("plaster")
    self_weight = SuperficialLoads.get_concrete_element_own_weight(slab.thickness / 100)
    slab.add_permanent_load(floor_covering + ceiling + self_weight)
    pavement.add_slab(slab)
    return pavement


# ---------------------------------------------------------------------------
# TestPavementToDict
# ---------------------------------------------------------------------------


class TestPavementToDict:
    """pavement_to_dict emits only construction inputs, in insertion order."""

    def test_pillar_count(self) -> None:
        result = pavement_to_dict(_build_pavement())
        assert len(result["pillars"]) == 4, "four pillars should be serialized"

    def test_beam_count(self) -> None:
        result = pavement_to_dict(_build_pavement())
        assert len(result["beams"]) == 4, "four beams should be serialized"

    def test_slab_count(self) -> None:
        result = pavement_to_dict(_build_pavement())
        assert len(result["slabs"]) == 1, "one slab should be serialized"

    def test_pillar_has_required_keys(self) -> None:
        result = pavement_to_dict(_build_pavement())
        pillar = result["pillars"][0]
        for key in ("id", "x", "y", "width", "depth"):
            assert key in pillar, f"pillar dict should contain '{key}'"

    def test_pillar_geometry_values(self) -> None:
        result = pavement_to_dict(_build_pavement())
        first = result["pillars"][0]
        assert first["x"] == 0, "first pillar x should be 0"
        assert first["y"] == 0, "first pillar y should be 0"
        assert first["width"] == 20, "first pillar width should be 20 cm"
        assert first["depth"] == 25, "first pillar depth should be 25 cm"

    def test_beam_alignment_is_string_value(self) -> None:
        result = pavement_to_dict(_build_pavement())
        # First beam is BOTTOM-aligned; Alignment.BOTTOM.value == "bottom"
        assert result["beams"][0]["alignment"] == "bottom", (
            "beam alignment should be the enum string value, not the enum member"
        )

    def test_beam_pillar_ids_is_list(self) -> None:
        result = pavement_to_dict(_build_pavement())
        assert isinstance(result["beams"][0]["pillar_ids"], list), (
            "pillar_ids should be serialized as a list"
        )

    def test_beam_has_nested_wall(self) -> None:
        result = pavement_to_dict(_build_pavement())
        beam = result["beams"][0]
        assert "wall" in beam, "beam dict should contain nested 'wall'"
        wall = beam["wall"]
        for key in (
            "structural",
            "masonry_type",
            "nominal_thickness",
            "coating_thickness",
        ):
            assert key in wall, f"wall dict should contain '{key}'"

    def test_beam_wall_values(self) -> None:
        result = pavement_to_dict(_build_pavement())
        wall = result["beams"][0]["wall"]
        assert wall["structural"] is False, "wall should not be structural"
        assert wall["masonry_type"] == "hollow concrete block", (
            "masonry type should match"
        )
        assert wall["nominal_thickness"] == 14, "nominal thickness should be 14 cm"
        assert wall["coating_thickness"] == 1, "coating thickness should be 1 cm"

    def test_beam_omits_resolved_keys(self) -> None:
        result = pavement_to_dict(_build_pavement())
        beam = result["beams"][0]
        for absent_key in ("height", "axis", "spans", "centerline"):
            assert absent_key not in beam, (
                f"resolved-only key '{absent_key}' should not be serialized"
            )

    def test_slab_corner_pillar_ids_is_list_of_four(self) -> None:
        result = pavement_to_dict(_build_pavement())
        corners = result["slabs"][0]["corner_pillar_ids"]
        assert isinstance(corners, list), "corner_pillar_ids should be a list"
        assert len(corners) == 4, "corner_pillar_ids should have 4 entries"

    def test_slab_local_preserved(self) -> None:
        result = pavement_to_dict(_build_pavement())
        assert result["slabs"][0]["local"] == "Bedrooms", (
            "slab local label should be preserved"
        )

    def test_slab_permanent_load_is_float(self) -> None:
        result = pavement_to_dict(_build_pavement())
        perm = result["slabs"][0]["permanent_load"]
        assert isinstance(perm, float), "permanent_load should be a float"
        assert perm > 0, "permanent_load should be positive"

    def test_slab_omits_resolved_keys(self) -> None:
        result = pavement_to_dict(_build_pavement())
        slab = result["slabs"][0]
        for absent_key in ("thickness", "variable_load"):
            assert absent_key not in slab, (
                f"resolved-only key '{absent_key}' should not be serialized"
            )

    def test_insertion_order_pillars(self) -> None:
        """Pillars appear in the same insertion order as add_pillar calls."""
        result = pavement_to_dict(_build_pavement())
        xs = [p["x"] for p in result["pillars"]]
        # build order: (0,0), (500,0), (0,400), (500,400)
        assert xs == [0, 500, 0, 500], (
            "pillars should appear in insertion order (x coords: 0,500,0,500)"
        )

    def test_top_level_keys(self) -> None:
        result = pavement_to_dict(_build_pavement())
        assert set(result.keys()) == {"pillars", "beams", "slabs"}, (
            "pavement_to_dict should emit exactly pillars, beams and slabs"
        )


# ---------------------------------------------------------------------------
# TestConfigToDict
# ---------------------------------------------------------------------------


class TestConfigToDict:
    """config_to_dict emits the 9 persisted fields and omits log settings."""

    def test_has_all_persisted_keys(self) -> None:
        result = config_to_dict(APP_CONFIG)
        expected_keys = {
            "aggregate",
            "max_aggregate_size",
            "max_bar_types",
            "max_layers",
            "pavement_concrete",
            "pavement_steel",
            "building_category",
            "exposure_class",
            "ceiling_height",
        }
        assert set(result.keys()) == expected_keys, (
            "config_to_dict should emit exactly the 9 persisted fields"
        )

    def test_omits_log_level(self) -> None:
        result = config_to_dict(APP_CONFIG)
        assert "log_level" not in result, (
            "log_level is a debug-only field and must not be persisted"
        )

    def test_omits_log_output(self) -> None:
        result = config_to_dict(APP_CONFIG)
        assert "log_output" not in result, (
            "log_output is a debug-only field and must not be persisted"
        )

    def test_default_aggregate(self) -> None:
        result = config_to_dict(AppConfig())
        assert result["aggregate"] == "granite", "default aggregate should be 'granite'"

    def test_default_pavement_concrete(self) -> None:
        result = config_to_dict(AppConfig())
        assert result["pavement_concrete"] == "C30", (
            "default pavement_concrete should be 'C30'"
        )

    def test_default_exposure_class(self) -> None:
        result = config_to_dict(AppConfig())
        assert result["exposure_class"] == 2, "default exposure class should be 2"

    def test_non_default_values_roundtrip(self) -> None:
        """Non-default field values survive config_to_dict."""
        cfg = AppConfig(aggregate="basalt", max_bar_types=2, exposure_class=4)
        result = config_to_dict(cfg)
        assert result["aggregate"] == "basalt", "aggregate should be 'basalt'"
        assert result["max_bar_types"] == 2, "max_bar_types should be 2"
        assert result["exposure_class"] == 4, "exposure_class should be 4"
