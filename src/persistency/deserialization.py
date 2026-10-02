"""Rebuild pavement domain objects from a plain dict."""

from __future__ import annotations

from collections.abc import Callable, Mapping
from typing import cast

from src.config import AppConfig
from src.pavement_elements.continuous_beam import ContinuousBeam, WallDefinition
from src.pavement_elements.geometry_utils import Alignment
from src.pavement_elements.pavement import Pavement
from src.pavement_elements.pillar import Pillar
from src.pavement_elements.slab import Slab
from src.persistency.schema import (
    BeamDict,
    ConfigDict,
    PavementDict,
    PillarDict,
    SlabDict,
    WallDict,
)

BEAM_CONTEXT = "Beam"
CONFIG_CONTEXT = "Config"
DOCUMENT_CONTEXT = "Document"
PILLAR_CONTEXT = "Pillar"
SLAB_CONTEXT = "Slab"
WALL_CONTEXT = "Wall"


def _require[T](
    data: Mapping[str, object], key: str, context: str, expected: type[T]
) -> T:
    """Fetches a required key from a mapping, raising a clear error if absent.

    The type parameter T is inferred from the expected argument.

    Args:
        data: The mapping to read from.
        key: The key that must be present.
        context: A short description of what is being parsed, used in the error message.
        expected: The type the value is expected to have; used only to infer T.

    Returns:
        The value stored at key, typed as T.

    Raises:
        ValueError: If key is missing from data.
    """
    if key not in data:
        raise ValueError(f"malformed pavement file: missing '{key}' in {context}")
    return cast(T, data[key])


def _wall_from_dict(data: WallDict) -> WallDefinition:
    """Rebuilds a wall definition from its serialized dict.

    Args:
        data: The serialized wall mapping.

    Returns:
        The reconstructed wall definition.

    Raises:
        ValueError: If a required key is missing.
    """
    return WallDefinition(
        structural=_require(data, "structural", WALL_CONTEXT, bool),
        masonry_type=_require(data, "masonry_type", WALL_CONTEXT, str),
        nominal_thickness=_require(data, "nominal_thickness", WALL_CONTEXT, float),
        coating_thickness=_require(data, "coating_thickness", WALL_CONTEXT, int),
    )


def _pillar_from_dict(data: PillarDict) -> Pillar:
    """Rebuilds a pillar from its serialized dict.

    The pillar receives a freshly generated id; the caller is responsible for
    mapping the saved id to it.

    Args:
        data: The serialized pillar mapping.

    Returns:
        The reconstructed pillar.

    Raises:
        ValueError: If a required key is missing.
    """
    return Pillar(
        x=_require(data, "x", PILLAR_CONTEXT, float),
        y=_require(data, "y", PILLAR_CONTEXT, float),
        width=_require(data, "width", PILLAR_CONTEXT, float),
        depth=_require(data, "depth", PILLAR_CONTEXT, float),
    )


def _beam_from_dict(data: BeamDict, remap: Callable[[str], str]) -> ContinuousBeam:
    """Rebuilds a continuous beam from its serialized dict.

    Pillar references are translated through remap so they point at the freshly
    reconstructed pillars.

    Args:
        data: The serialized beam mapping.
        remap: Translates a saved pillar id to its reconstructed id.

    Returns:
        The reconstructed continuous beam.

    Raises:
        ValueError: If a required key is missing, the alignment is invalid, or a pillar reference is unknown.
    """
    wall = _wall_from_dict(cast(WallDict, _require(data, "wall", BEAM_CONTEXT, dict)))
    alignment_value = _require(data, "alignment", BEAM_CONTEXT, str)

    try:
        alignment = Alignment(alignment_value)
    except ValueError:
        raise ValueError(
            f"malformed pavement file: invalid beam alignment '{alignment_value}'"
        )

    return ContinuousBeam(
        pillar_ids=[
            remap(pid)
            for pid in cast(list[str], _require(data, "pillar_ids", BEAM_CONTEXT, list))
        ],
        reference_pillar_id=remap(
            _require(data, "reference_pillar_id", BEAM_CONTEXT, str)
        ),
        width=_require(data, "width", BEAM_CONTEXT, float),
        alignment=alignment,
        wall=wall,
    )


def _slab_from_dict(data: SlabDict, remap: Callable[[str], str]) -> Slab:
    """Rebuilds a slab from its serialized dict.

    Corner pillar references are translated through remap so they point at the
    freshly reconstructed pillars.

    Args:
        data: The serialized slab mapping.
        remap: Translates a saved pillar id to its reconstructed id.

    Returns:
        The reconstructed slab, with its permanent load restored. A missing
        lowered key (older files) defaults to 0 cm.

    Raises:
        ValueError: If a required key is missing or a pillar reference is unknown.
    """
    corners = tuple(
        remap(pid)
        for pid in cast(
            list[str], _require(data, "corner_pillar_ids", SLAB_CONTEXT, list)
        )
    )
    slab = Slab(
        corner_pillar_ids=cast(tuple[str, str, str, str], corners),
        local=_require(data, "local", SLAB_CONTEXT, str),
        lowered=data.get("lowered", 0),
    )
    slab.add_permanent_load(_require(data, "permanent_load", SLAB_CONTEXT, float))
    return slab


def pavement_from_dict(data: PavementDict) -> Pavement:
    """Rebuilds an unresolved pavement from a plain dict.

    Pillars are recreated first so that a mapping from each saved pillar id to its freshly generated id can be built; beam and slab pillar references are translated through that mapping before the elements are constructed. The returned pavement mirrors a freshly built one: the caller is expected to run resolve() next.

    Args:
        data: A dict as produced by pavement_to_dict.

    Returns:
        The reconstructed, unresolved pavement.

    Raises:
        ValueError: If a required key is missing, an enum value is invalid, or a beam/slab references an unknown pillar.
    """
    pavement = Pavement()
    id_map: dict[str, str] = {}  # saved pillar id -> newly generated pillar id

    for pillar_data in cast(
        list[PillarDict], _require(data, "pillars", DOCUMENT_CONTEXT, list)
    ):
        pillar = _pillar_from_dict(pillar_data)
        saved_id = _require(pillar_data, "id", PILLAR_CONTEXT, str)
        id_map[saved_id] = pillar.id
        pavement.add_pillar(pillar)

    def _remap(old_id: str) -> str:
        """Translates a saved pillar id to its reconstructed id.

        Args:
            old_id: The pillar id stored in the file.

        Returns:
            The id of the freshly reconstructed pillar.

        Raises:
            ValueError: If old_id was not among the file's pillars.
        """
        try:
            return id_map[old_id]
        except KeyError:
            raise ValueError(
                f"malformed pavement file: references unknown pillar '{old_id}'"
            ) from None

    for beam_data in cast(
        list[BeamDict], _require(data, "beams", DOCUMENT_CONTEXT, list)
    ):
        pavement.add_beam(_beam_from_dict(beam_data, _remap))

    for slab_data in cast(
        list[SlabDict], _require(data, "slabs", DOCUMENT_CONTEXT, list)
    ):
        pavement.add_slab(_slab_from_dict(slab_data, _remap))

    return pavement


def config_from_dict(data: ConfigDict) -> AppConfig:
    """Rebuilds an AppConfig from its serialized dict.

    Args:
        data: The serialized config mapping.

    Returns:
        The reconstructed AppConfig.

    Raises:
        ValueError: If a required key is missing.
    """
    return AppConfig(
        aggregate=_require(data, "aggregate", CONFIG_CONTEXT, str),
        max_aggregate_size=_require(data, "max_aggregate_size", CONFIG_CONTEXT, float),
        max_bar_types=_require(data, "max_bar_types", CONFIG_CONTEXT, int),
        max_layers=_require(data, "max_layers", CONFIG_CONTEXT, int),
        pavement_concrete=_require(data, "pavement_concrete", CONFIG_CONTEXT, str),
        pavement_steel=_require(data, "pavement_steel", CONFIG_CONTEXT, str),
        building_category=_require(data, "building_category", CONFIG_CONTEXT, str),
        exposure_class=_require(data, "exposure_class", CONFIG_CONTEXT, int),
        ceiling_height=_require(data, "ceiling_height", CONFIG_CONTEXT, float),
    )
