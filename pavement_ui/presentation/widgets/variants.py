"""Style variants of buttons, read by the stylesheet's ``variant`` property."""

from typing import Literal

from PySide6.QtWidgets import QWidget

type Variant = Literal["primary", "destructive"]


def set_variant(widget: QWidget, variant: Variant) -> None:
    """Mark a widget as primary or destructive and re-apply the stylesheet"""
    widget.setProperty("variant", variant)
    widget.style().unpolish(widget)
    widget.style().polish(widget)
