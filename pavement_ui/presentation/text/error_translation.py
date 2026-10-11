"""Translate engine messages and file errors into pt-BR."""

import re

from pavement_ui.core.errors import PersistenceError, PersistenceErrorKind
from pavement_ui.presentation.text.error_patterns import PATTERNS
from pavement_ui.presentation.text.option_labels import OptionKind, label
from pavement_ui.presentation.text.strings import dialogs as s

_QUOTED = re.compile(r"'([^']*)'")  # 'P2', 'P3' in engine lists of IDs


def _convert(name: str, value: str) -> str:
    """Convert one captured group by its name prefix (see error_patterns)."""
    if name.startswith("num"):
        return value.replace(".", ",")
    if name == "edge":
        return label(OptionKind.EDGE, value)
    if name == "rest":
        return translate(value)
    if name == "ids":
        return _QUOTED.sub(r"“\1”", value)
    return value


def _render(template: str, match: re.Match[str]) -> str:
    groups = {name: _convert(name, value) for name, value in match.groupdict().items()}
    return template.format(**groups)


def translate(message: str) -> str:
    """Return the pt-BR text of an engine message, or the message itself if unknown

    Args:
        message: The engine's original (English) text.
    """
    for entry in PATTERNS:
        match = entry.pattern.match(message.strip())
        if match is not None:
            return _render(entry.template, match)
    return message


def file_error_text(error: PersistenceError) -> str:
    """Return the pt-BR description of a project file error"""
    match error.kind:
        case PersistenceErrorKind.NOT_FOUND:
            return s.FILE_NOT_FOUND.format(path=error.detail)
        case PersistenceErrorKind.INVALID_YAML:
            return s.FILE_INVALID_YAML.format(line=error.detail)
        case PersistenceErrorKind.INVALID_CONTENT:
            return s.FILE_INVALID_CONTENT.format(detail=translate(error.detail))
        case PersistenceErrorKind.WRITE_FAILED:
            return s.FILE_WRITE_FAILED.format(detail=error.detail)
