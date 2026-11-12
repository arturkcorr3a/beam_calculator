"""DrawingView: a vector drawing in a graphics view, with wheel zoom and drag pan."""

from PySide6.QtCore import QRectF, Qt
from PySide6.QtGui import (
    QBrush,
    QColor,
    QPainter,
    QPen,
    QPicture,
    QResizeEvent,
    QWheelEvent,
)
from PySide6.QtWidgets import (
    QGraphicsItem,
    QGraphicsRectItem,
    QGraphicsScene,
    QGraphicsView,
    QStyleOptionGraphicsItem,
    QWidget,
)

from pavement_ui.core.results.vector_drawing import VectorDrawing
from pavement_ui.presentation.report.painters.vector_painter import paint_vector
from pavement_ui.presentation.theme import tokens

_STEP = 1.25  # zoom factor of one wheel notch or one button press
_WHEEL_NOTCH = 120.0
_MAX_PX_PER_CM = 60.0  # the deepest zoom
_MIN_FIT_RATIO = 0.25  # the widest zoom, as a fraction of the fitted one
_SCENE_MARGIN = 0.03  # room around the sheet, as a fraction of its size
_SHADOW_OFFSET_CM = 8.0  # of the paper's drop shadow, in model cm
_SHADOW_COLOR = "#B4BAC0"


class _DrawingItem(QGraphicsItem):
    """The drawing in model cm, y up, recorded once and replayed on each paint"""

    def __init__(self, drawing: VectorDrawing) -> None:
        super().__init__()
        x0, y0, x1, y1 = drawing.bounds
        self._rect = QRectF(x0, -y1, x1 - x0, y1 - y0)
        self._picture = QPicture()
        painter = QPainter(self._picture)
        paint_vector(painter, drawing, self._rect, margin=0.0, cosmetic=True)
        painter.end()

    def boundingRect(self) -> QRectF:
        return self._rect

    def paint(
        self,
        painter: QPainter,
        option: QStyleOptionGraphicsItem,
        widget: QWidget | None = None,
    ) -> None:
        self._picture.play(painter)


def _add_paper(scene: QGraphicsScene, rect: QRectF) -> None:
    """Add the sheet's white paper with a thin edge and a shadow, under the drawing

    The margins of the frame (20 mm on the left, 10 mm elsewhere) show as the white strip between the paper's edge and the frame.
    """
    shadow = scene.addRect(
        rect.translated(_SHADOW_OFFSET_CM, _SHADOW_OFFSET_CM),
        QPen(Qt.PenStyle.NoPen),
        QBrush(QColor(_SHADOW_COLOR)),
    )
    pen = QPen(QColor(tokens.BORDER_INPUT), 1.0)
    pen.setCosmetic(True)
    paper: QGraphicsRectItem = scene.addRect(rect, pen, QBrush(QColor(tokens.SURFACE)))
    shadow.setZValue(-2)
    paper.setZValue(-1)


class DrawingView(QGraphicsView):
    """Shows one drawing; the wheel zooms under the cursor and dragging pans"""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("drawingView")
        self.setScene(QGraphicsScene(self))
        self.setBackgroundBrush(QColor(tokens.SURFACE))
        self.setRenderHints(
            QPainter.RenderHint.Antialiasing | QPainter.RenderHint.TextAntialiasing
        )
        self.setDragMode(QGraphicsView.DragMode.ScrollHandDrag)
        self.setTransformationAnchor(QGraphicsView.ViewportAnchor.AnchorUnderMouse)
        self.setResizeAnchor(QGraphicsView.ViewportAnchor.AnchorViewCenter)
        self._fitted_scale = 1.0
        self._user_zoomed = False

    def set_drawing(self, drawing: VectorDrawing) -> None:
        """Show a new drawing, fitted to the view"""
        scene = self.scene()
        scene.clear()
        item = _DrawingItem(drawing)
        rect = item.boundingRect()
        on_paper = drawing.paper_mm is not None
        self.setBackgroundBrush(
            QColor(tokens.STATUS_BG if on_paper else tokens.SURFACE)
        )
        if on_paper:
            _add_paper(scene, rect)
        scene.addItem(item)
        scene.setSceneRect(
            rect.adjusted(
                -rect.width() * _SCENE_MARGIN,
                -rect.height() * _SCENE_MARGIN,
                rect.width() * _SCENE_MARGIN,
                rect.height() * _SCENE_MARGIN,
            )
        )
        self.fit()

    def fit(self) -> None:
        """Show the whole drawing"""
        self.fitInView(self.sceneRect(), Qt.AspectRatioMode.KeepAspectRatio)
        self._fitted_scale = self.transform().m11()
        self._user_zoomed = False

    def zoom(self, factor: float) -> None:
        """Zoom by factor, within the deepest and the widest zooms"""
        current = self.transform().m11()
        target = min(
            max(current * factor, self._fitted_scale * _MIN_FIT_RATIO),
            _MAX_PX_PER_CM,
        )
        self.scale(target / current, target / current)
        self._user_zoomed = True

    def zoom_in(self) -> None:
        self._zoom_at_center(_STEP)

    def zoom_out(self) -> None:
        self._zoom_at_center(1 / _STEP)

    def _zoom_at_center(self, factor: float) -> None:
        self.setTransformationAnchor(QGraphicsView.ViewportAnchor.AnchorViewCenter)
        self.zoom(factor)
        self.setTransformationAnchor(QGraphicsView.ViewportAnchor.AnchorUnderMouse)

    def wheelEvent(self, event: QWheelEvent) -> None:
        self.zoom(_STEP ** (event.angleDelta().y() / _WHEEL_NOTCH))
        event.accept()

    def resizeEvent(self, event: QResizeEvent) -> None:
        super().resizeEvent(event)
        if not self._user_zoomed:
            self.fit()
