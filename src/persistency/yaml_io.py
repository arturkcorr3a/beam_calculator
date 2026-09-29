"""Read and write pavement configurations as YAML files.

This is the only module that imports the ``yaml`` library; the object<->dict
mapping lives in the serialization/deserialization layers, keeping the wire
format isolated from the mapping logic.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, cast

import yaml

from src.config import APP_CONFIG
from src.pavement_elements.pavement import Pavement
from src.persistency.deserialization import config_from_dict, pavement_from_dict
from src.persistency.schema import ConfigDict, PavementDict
from src.persistency.serialization import config_to_dict, pavement_to_dict


def save_pavement(pavement: Pavement, path: str | Path) -> None:
    """Writes a pavement configuration and the current AppConfig to a YAML file.

    Args:
        pavement: The pavement to persist.
        path: Destination file path; parent directories are created if needed.
    """
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    document: dict[str, Any] = {
        **pavement_to_dict(pavement),
        "config": config_to_dict(APP_CONFIG),
    }
    with path.open("w", encoding="utf-8") as file:
        yaml.safe_dump(
            document,
            file,
            sort_keys=False,
            allow_unicode=True,
            default_flow_style=False,
        )


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
        ValueError: If the file is malformed (see pavement_from_dict / config_from_dict).
    """
    with Path(path).open("r", encoding="utf-8") as file:
        data: dict[str, Any] = yaml.safe_load(file)

    if "config" in data:
        loaded_config = config_from_dict(cast(ConfigDict, data["config"]))
        for field in config_to_dict(loaded_config):
            setattr(APP_CONFIG, field, getattr(loaded_config, field))

    return pavement_from_dict(cast(PavementDict, data))
