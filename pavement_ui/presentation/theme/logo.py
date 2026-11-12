"""Logo assets from ``resources/beam_calculator_logo``; missing files give null images."""

from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtGui import QIcon, QImage, QPixmap

_LOGO_DIR = Path(__file__).parents[3] / "resources" / "beam_calculator_logo" / "png"
_ICON_FILES = (
    "icon/favicon-16.png",
    "icon/favicon-32.png",
    "icon/favicon-48.png",
    "icon/beam-app-icon-512.png",
)


def app_icon() -> QIcon:
    """Application icon; the simplified favicons serve the small sizes"""
    icon = QIcon()
    for name in _ICON_FILES:
        icon.addFile(str(_LOGO_DIR / name))
    return icon


def logo_pixmap(height_px: int, device_pixel_ratio: float) -> QPixmap:
    """Horizontal color logo scaled to height_px logical pixels"""
    pixmap = QPixmap(str(_LOGO_DIR / "horizontal/beam-horizontal-color@2x.png"))
    if pixmap.isNull():
        return pixmap
    scaled = pixmap.scaledToHeight(
        round(height_px * device_pixel_ratio),
        Qt.TransformationMode.SmoothTransformation,
    )
    scaled.setDevicePixelRatio(device_pixel_ratio)
    return scaled


def report_logo() -> QImage:
    """Print-resolution horizontal color logo for report pages"""
    return QImage(str(_LOGO_DIR / "horizontal/beam-horizontal-color@4x.png"))
