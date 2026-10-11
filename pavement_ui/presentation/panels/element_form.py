"""Base class of the inclusion forms (pillar, beam, slab)."""

from PySide6.QtCore import Signal
from PySide6.QtWidgets import QWidget

from pavement_ui.core.session import ProjectSession


class ElementForm(QWidget):
    """The fields of one element kind; ``ElementPanel`` decides what to do with them

    Signals:
        submit_requested: Enter was pressed in the form's last field.
        availability_changed: Whether inclusion is possible changed (e.g. a
            building category without slab usages).
    """

    submit_requested = Signal()
    availability_changed = Signal(bool)

    def include(self, session: ProjectSession) -> str:
        """Register the element described by the fields

        Returns:
            The new element's ID.

        Raises:
            EngineRuleError: If the engine refuses the element.
        """
        raise NotImplementedError

    def focus_first(self) -> None:
        """Put the keyboard focus on the first field"""
        raise NotImplementedError

    def is_available(self) -> bool:
        """Whether an element can be included now"""
        return True
