"""The name of a pavement project, taken from its file name."""

from pathlib import Path

PAVEMENT_SUFFIXES = (".pavement.yaml", ".pavement.yml")


def project_name(path: Path) -> str:
    """The file name without its ".pavement.yaml" ending (or else its last suffix)

    e.g. "residencial.pavement.yaml" -> "residencial".
    """
    for suffix in PAVEMENT_SUFFIXES:
        if path.name.lower().endswith(suffix):
            return path.name[: -len(suffix)]
    return path.stem
