"""Read and write pavement configurations as YAML files.

This is the only module that imports the ``yaml`` library; the object<->dict
mapping lives in the serialization/deserialization layers, keeping the wire
format isolated from the mapping logic.

Saved files are laid out for people to read and edit by hand: a header with the
units, one commented section per top-level key separated by blank lines,
sequences indented under their key, a blank line between list items, and lists
of plain values (pillar ids) written inline as ``[P1, P2]``.
"""

from __future__ import annotations

import textwrap
from pathlib import Path
from typing import Any, cast

import yaml

from src.config import APP_CONFIG
from src.errors import MalformedFileError
from src.pavement_elements.pavement import Pavement
from src.persistency.deserialization import config_from_dict, pavement_from_dict
from src.persistency.schema import ConfigDict, PavementDict
from src.persistency.serialization import config_to_dict, pavement_to_dict

HEADER = (
    "# beam_calculator — pavimento\n"
    "# Unidades: coordenadas e dimensões em cm, cargas em kN/m², pé-direito em m.\n"
    "# Modelo comentado, com todos os campos e valores aceitos: template.pavement.yaml,\n"
    "# na pasta de exemplos.\n"
)

# Top-level key -> comment written above its section, in document order
SECTION_COMMENTS: dict[str, str] = {
    "pillars": "Pilares: centro (x, y) e seção (width × depth), em cm",
    "beams": "Vigas contínuas: pilares em ordem, largura (cm), alinhamento e parede",
    "slabs": (
        "Lajes: pilares de canto, uso (NBR 6120), carga permanente sem o peso "
        "próprio (kN/m²) e rebaixo (cm)"
    ),
    "config": "Configurações: materiais, detalhamento, agressividade e pé-direito",
}

_INDENT = "  "
_LINE_WIDTH = 4096  # never wrap the inline id lists
_SEQUENCE_TAG = "tag:yaml.org,2002:seq"


class _PavementDumper(yaml.SafeDumper):
    """SafeDumper that indents block sequences under their parent key"""

    def increase_indent(self, flow: bool = False, indentless: bool = False) -> None:
        """Never emit an indentless sequence (``key:\\n- item``)"""
        super().increase_indent(flow, False)


def _represent_list(dumper: yaml.SafeDumper, data: list[Any]) -> yaml.Node:
    """Write lists of plain values inline (``[P1, P2]``) and the rest as blocks"""
    inline = all(not isinstance(item, dict | list) for item in data)
    return dumper.represent_sequence(_SEQUENCE_TAG, data, flow_style=inline)


_PavementDumper.add_representer(list, _represent_list)


def _dump(data: object) -> str:
    """Dump data as block-style YAML with the pavement dumper"""
    return yaml.dump(
        data,
        Dumper=_PavementDumper,
        sort_keys=False,
        allow_unicode=True,
        default_flow_style=False,
        width=_LINE_WIDTH,
    )


def _list_section(key: str, items: list[object]) -> str:
    """Render ``key:`` followed by its indented items, one blank line apart"""
    if not items:
        return f"{key}: []\n"
    blocks = [textwrap.indent(_dump([item]), _INDENT) for item in items]
    return f"{key}:\n" + "\n".join(blocks)


def _render(document: dict[str, object]) -> str:
    """Render the whole document: header, then one commented section per key"""
    parts = [HEADER]
    for key, value in document.items():
        body = (
            _list_section(key, cast(list[object], value))
            if isinstance(value, list)
            else _dump({key: value})
        )
        parts.append(f"\n# {SECTION_COMMENTS[key]}\n{body}")
    return "".join(parts)


def save_pavement(pavement: Pavement, path: str | Path) -> None:
    """Writes a pavement configuration and the current AppConfig to a YAML file.

    Args:
        pavement: The pavement to persist.
        path: Destination file path; parent directories are created if needed.
    """
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    document: dict[str, object] = {
        **pavement_to_dict(pavement),
        "config": config_to_dict(APP_CONFIG),
    }
    path.write_text(_render(document), encoding="utf-8")


def load_pavement(path: str | Path) -> Pavement:
    """Reads a pavement configuration from a YAML file.

    If the file contains a ``config`` section, the fields are applied to
    ``APP_CONFIG`` in place so the rest of the application immediately reflects
    the saved settings.

    The returned pavement is unresolved; call resolve() on it to size the
    structure.

    Args:
        path: Path to a YAML file previously written by save_pavement.

    Returns:
        The reconstructed, unresolved pavement.

    Raises:
        MalformedFileError: If the file is empty, its top level is not a
            mapping, or it is otherwise malformed (see pavement_from_dict /
            config_from_dict).
    """
    with Path(path).open("r", encoding="utf-8") as file:
        data: object = yaml.safe_load(file)

    if not isinstance(data, dict):
        raise MalformedFileError("expected a mapping at the top level")
    document = cast(dict[str, Any], data)

    if "config" in document:
        loaded_config = config_from_dict(cast(ConfigDict, document["config"]))
        for field in config_to_dict(loaded_config):
            setattr(APP_CONFIG, field, getattr(loaded_config, field))

    return pavement_from_dict(cast(PavementDict, document))
