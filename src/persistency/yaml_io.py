"""Read and write pavement configurations as YAML files.

This is the only module that imports the ``yaml`` library; the object<->dict
mapping lives in the serialization/deserialization layers, keeping the wire
format isolated from the mapping logic.
"""

from __future__ import annotations

from pathlib import Path

import yaml

from src.pavement.pavement import Pavement
from src.persistency.deserialization import pavement_from_dict
from src.persistency.schema import PavementDict
from src.persistency.serialization import pavement_to_dict


def save_pavement(pavement: Pavement, path: str | Path) -> None:
    """Writes a pavement configuration to a YAML file.

    Args:
        pavement: The pavement to persist.
        path: Destination file path; parent directories are created if needed.
    """
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as file:
        yaml.safe_dump(
            pavement_to_dict(pavement),
            file,
            sort_keys=False,
            allow_unicode=True,
            default_flow_style=False,
        )


def load_pavement(path: str | Path) -> Pavement:
    """Reads a pavement configuration from a YAML file.

    The returned pavement is unresolved; call resolve() on it to size the
    structure.

    Args:
        path: Path to a YAML file previously written by save_pavement.

    Returns:
        The reconstructed, unresolved pavement.

    Raises:
        ValueError: If the file is malformed (see pavement_from_dict).
    """
    with Path(path).open("r", encoding="utf-8") as file:
        data: PavementDict = yaml.safe_load(file)
    return pavement_from_dict(data)
