"""Texts of the main window."""

from pavement_ui.presentation.text.strings.common import APP_NAME, UNTITLED


def window_title(file_name: str | None) -> str:
    """Build the main window title, e.g. "Pavement Designer — exemplo.yaml"

    Args:
        file_name: Name of the open project file, or None when unsaved.
    """
    return f"{APP_NAME} — {file_name or UNTITLED}"
