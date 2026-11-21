"""YamlIsolatedBeamStore: isolated beam files (``*.beam.yaml``) with the project settings.

The file holds the beam (section, spans, pillars, loads) and the project
settings in the engine's ``config`` format, so it reopens exactly as saved.
Load spans are written 1-based (V1, V2…); a load without ``span`` acts on
every span.
"""

from collections.abc import Callable
from pathlib import Path
from typing import cast

import yaml

from pavement_ui.core.engine import config_mapper, element_factory
from pavement_ui.core.engine.project_store import yaml_error_line
from pavement_ui.core.engine.rule_errors import rule_message
from pavement_ui.core.errors import PersistenceError, PersistenceErrorKind
from pavement_ui.core.model.isolated_beam_input import (
    CustomLoad,
    IsolatedBeamInput,
    IsolatedLoadInput,
    IsolatedPillarInput,
    OwnWeightLoad,
    WallLoad,
)
from pavement_ui.core.model.records import WallRecord
from pavement_ui.core.model.settings import ConfigValues
from pavement_ui.core.ports import LoadedIsolatedBeam
from src.logger import suppress_logging
from src.persistency.schema import ConfigDict

HEADER = (
    "# beam_calculator — viga isolada\n"
    "# Unidades: seção e pilares em cm, vãos e altura de parede em m, cargas em kN/m.\n"
    "# O vão de uma carga começa em 1 (V1); sem 'span', vale para todos os vãos.\n"
)
NOT_AN_ISOLATED_BEAM = "Not an isolated beam file."
INVALID_FIELD = "Invalid isolated beam field '{field}'."

_OWN_WEIGHT, _WALL, _CUSTOM = "own_weight", "wall", "custom"
_LINE_WIDTH = 4096  # never wrap the inline mappings

type _Doc = dict[str, object]


# --- writing --------------------------------------------------------------------


def _span(index: int | None) -> _Doc:
    return {} if index is None else {"span": index + 1}


def _wall_to_dict(wall: WallRecord) -> _Doc:
    """Same keys as a pavement beam's wall"""
    return {
        "masonry_type": wall.masonry_key,
        "nominal_thickness": wall.nominal_thickness_cm,
        "coating_thickness": wall.coating_cm,
    }


def _load_to_dict(load: IsolatedLoadInput) -> _Doc:
    match load:
        case OwnWeightLoad():
            return {"type": _OWN_WEIGHT, **_span(load.span_index)}
        case WallLoad():
            return {
                "type": _WALL,
                **_span(load.span_index),
                "height": load.height_m,
                "wall": _wall_to_dict(load.wall),
            }
        case CustomLoad():
            return {
                "type": _CUSTOM,
                **_span(load.span_index),
                "label": load.label,
                "value": load.value_kn_m,
                "variable": load.variable,
                "psi_2": load.psi_2,
            }


def _dump(key: str, value: object, flow: bool | None) -> str:
    """One top-level key; flow None writes the innermost collections inline"""
    return yaml.safe_dump(
        {key: value},
        sort_keys=False,
        allow_unicode=True,
        default_flow_style=flow,
        width=_LINE_WIDTH,
    )


def _render(data: IsolatedBeamInput, config: ConfigValues) -> str:
    sections = (
        _dump("section", {"width": data.width_cm, "height": data.height_cm}, None),
        _dump("spans", list(data.span_lengths_m), None),
        _dump(
            "pillars",
            [{"width": p.width_cm, "depth": p.depth_cm} for p in data.pillars],
            None,
        ),
        _dump("loads", [_load_to_dict(load) for load in data.loads], None),
        _dump("config", config_mapper.to_dict(config), False),
    )
    return HEADER + "\n" + "\n".join(sections)


# --- reading --------------------------------------------------------------------


def _invalid(field: str) -> ValueError:
    return ValueError(INVALID_FIELD.format(field=field))


def _mapping(value: object, field: str) -> _Doc:
    if not isinstance(value, dict):
        raise _invalid(field)
    return cast(_Doc, value)


def _sequence(value: object, field: str) -> list[object]:
    if not isinstance(value, list):
        raise _invalid(field)
    return cast(list[object], value)


def _get(data: _Doc, key: str, field: str) -> object:
    if key not in data:
        raise _invalid(f"{field}.{key}" if field else key)
    return data[key]


def _number(
    value: object, field: str, accept: Callable[[float], bool] = lambda v: v > 0
) -> float:
    """A number (not a bool) for which accept holds; positive by default"""
    if isinstance(value, bool) or not isinstance(value, int | float):
        raise _invalid(field)
    if not accept(float(value)):
        raise _invalid(field)
    return float(value)


def _flag(value: object, field: str) -> bool:
    if not isinstance(value, bool):
        raise _invalid(field)
    return value


def _span_index(load: _Doc, span_count: int, field: str) -> int | None:
    """The zero-based span of a load; None when it has no ``span``"""
    value = load.get("span")
    if value is None:
        return None
    if isinstance(value, bool) or not isinstance(value, int):
        raise _invalid(f"{field}.span")
    if not 1 <= value <= span_count:
        raise _invalid(f"{field}.span")
    return value - 1


def _wall_from(value: object, field: str) -> WallRecord:
    data = _mapping(value, field)
    if "structural" in data:  # structural masonry was removed
        raise _invalid(f"{field}.structural")
    coating = _get(data, "coating_thickness", field)
    if isinstance(coating, bool) or not isinstance(coating, int):
        raise _invalid(f"{field}.coating_thickness")
    record = WallRecord(
        masonry_key=str(_get(data, "masonry_type", field)),
        nominal_thickness_cm=_number(
            _get(data, "nominal_thickness", field), f"{field}.nominal_thickness"
        ),
        coating_cm=coating,
    )
    # the NBR 6120 Table 2 lookup raises KeyError for an unknown wall
    element_factory.wall(record).get_parameters_for_load()
    return record


def _load_from(value: object, span_count: int, field: str) -> IsolatedLoadInput:
    data = _mapping(value, field)
    span = _span_index(data, span_count, field)
    match _get(data, "type", field):
        case "own_weight":
            return OwnWeightLoad(span)
        case "wall":
            return WallLoad(
                wall=_wall_from(_get(data, "wall", field), f"{field}.wall"),
                height_m=_number(_get(data, "height", field), f"{field}.height"),
                span_index=span,
            )
        case "custom":
            return CustomLoad(
                label=str(_get(data, "label", field)),
                value_kn_m=_number(
                    _get(data, "value", field), f"{field}.value", lambda v: v >= 0
                ),
                variable=_flag(data.get("variable", False), f"{field}.variable"),
                psi_2=_number(
                    data.get("psi_2", 0.3), f"{field}.psi_2", lambda v: 0 <= v <= 1
                ),
                span_index=span,
            )
        case _:
            raise _invalid(f"{field}.type")


def _from_document(document: object) -> LoadedIsolatedBeam:
    if not isinstance(document, dict) or "section" not in document:
        raise ValueError(NOT_AN_ISOLATED_BEAM)
    data = cast(_Doc, document)
    section = _mapping(data["section"], "section")
    spans = [
        _number(value, f"spans[{i}]")
        for i, value in enumerate(_sequence(_get(data, "spans", ""), "spans"), 1)
    ]
    pillar_items = _sequence(_get(data, "pillars", ""), "pillars")
    if not spans or len(pillar_items) != len(spans) + 1:
        raise _invalid("pillars")
    pillars: list[IsolatedPillarInput] = []
    for i, item in enumerate(pillar_items, 1):
        pillar, field = _mapping(item, f"pillars[{i}]"), f"pillars[{i}]"
        pillars.append(
            IsolatedPillarInput(
                width_cm=_number(_get(pillar, "width", field), f"{field}.width"),
                depth_cm=_number(_get(pillar, "depth", field), f"{field}.depth"),
            )
        )
    loads = tuple(
        _load_from(item, len(spans), f"loads[{i}]")
        for i, item in enumerate(_sequence(_get(data, "loads", ""), "loads"), 1)
    )
    beam = IsolatedBeamInput(
        width_cm=_number(_get(section, "width", "section"), "section.width"),
        height_cm=_number(_get(section, "height", "section"), "section.height"),
        span_lengths_m=tuple(spans),
        pillars=tuple(pillars),
        loads=loads,
    )
    config = config_mapper.from_dict(
        cast(ConfigDict, _mapping(_get(data, "config", ""), "config"))
    )
    return LoadedIsolatedBeam(beam, config)


class YamlIsolatedBeamStore:
    """Save and open isolated beam files"""

    def save(self, path: Path, data: IsolatedBeamInput, config: ConfigValues) -> None:
        """Write the beam and the settings to path

        Raises:
            PersistenceError: If the file cannot be written.
        """
        try:
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(_render(data, config), encoding="utf-8")
        except OSError as error:
            raise PersistenceError(
                PersistenceErrorKind.WRITE_FAILED, str(error)
            ) from error

    def open(self, path: Path) -> LoadedIsolatedBeam:
        """Read the beam and the settings from path

        Raises:
            PersistenceError: If the file is missing, is not YAML, or is not a
                valid isolated beam.
        """
        try:
            with path.open(encoding="utf-8") as file:
                document: object = yaml.safe_load(file)
            with suppress_logging():
                return _from_document(document)
        except FileNotFoundError as error:
            raise PersistenceError(PersistenceErrorKind.NOT_FOUND, str(path)) from error
        except yaml.YAMLError as error:
            raise PersistenceError(
                PersistenceErrorKind.INVALID_YAML, yaml_error_line(error)
            ) from error
        except (ValueError, KeyError) as error:
            raise PersistenceError(
                PersistenceErrorKind.INVALID_CONTENT, rule_message(error)
            ) from error
        except TypeError as error:
            raise PersistenceError(
                PersistenceErrorKind.INVALID_CONTENT, str(error)
            ) from error
