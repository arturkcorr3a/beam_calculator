"""PlanView: Y-up view of the plan with zoom, pan, fit, click and cursor tracking."""

from PySide6.QtCore import QEvent, QPoint, QRect, QRectF, Qt, Signal
from PySide6.QtGui import QKeyEvent, QMouseEvent, QPainter, QWheelEvent
from PySide6.QtWidgets import QGraphicsView, QWidget

from pavement_ui.presentation.plan.axis_glyph import draw_axis_glyph
from pavement_ui.presentation.plan.items.element_item import element_of
from pavement_ui.presentation.plan.plan_scene import PlanScene
from pavement_ui.presentation.plan.scene_units import to_meters

_ZOOM_STEP = 1.15
_FIT_MARGIN = 0.10
_MIN_FIT_MARGIN = 80.0  # cm; room for the dimension labels


class PlanView(QGraphicsView):
    """Signals:
    item_clicked: (kind, id) of the element under a left click.
    cursor_moved: (x_m, y_m) of the cursor, or (None, None) when it leaves.
    """

    item_clicked = Signal(object, str)
    cursor_moved = Signal(object, object)

    def __init__(self, scene: PlanScene, parent: QWidget | None = None) -> None:
        super().__init__(scene, parent)
        self._scene = scene
        self.setObjectName("planView")
        self.setRenderHint(QPainter.RenderHint.Antialiasing)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.setTransformationAnchor(QGraphicsView.ViewportAnchor.AnchorUnderMouse)
        self.setResizeAnchor(QGraphicsView.ViewportAnchor.AnchorViewCenter)
        self.setMouseTracking(True)
        self.scale(1.0, -1.0)  # Y up
        self._space_down = False
        self._pan_from: QPoint | None = None
        self.user_moved = False  # zoomed or panned by hand since the last fit

    # --- zoom and fit ------------------------------------------------------------

    def zoom(self, factor: float) -> None:
        self.scale(factor, factor)
        self.user_moved = True

    def zoom_centered(self, factor: float) -> None:
        anchor = self.transformationAnchor()
        self.setTransformationAnchor(QGraphicsView.ViewportAnchor.AnchorViewCenter)
        self.zoom(factor)
        self.setTransformationAnchor(anchor)

    def fit(self) -> None:
        """Show every element with a 10 % margin, keeping the aspect ratio"""
        self.user_moved = False
        bounds = self._scene.bounds
        if bounds is None:
            return
        margin_x = max(bounds.width() * _FIT_MARGIN, _MIN_FIT_MARGIN)
        margin_y = max(bounds.height() * _FIT_MARGIN, _MIN_FIT_MARGIN)
        rect = QRectF(bounds).adjusted(-margin_x, -margin_y, margin_x, margin_y)
        self.fitInView(rect, Qt.AspectRatioMode.KeepAspectRatio)

    def wheelEvent(self, event: QWheelEvent) -> None:
        steps = event.angleDelta().y() / 120
        self.zoom(_ZOOM_STEP**steps)

    # --- pan, click, cursor ------------------------------------------------------

    def _pans(self, event: QMouseEvent) -> bool:
        button = event.button()
        return button == Qt.MouseButton.MiddleButton or (
            button == Qt.MouseButton.LeftButton and self._space_down
        )

    def mousePressEvent(self, event: QMouseEvent) -> None:
        if self._pans(event):
            self._pan_from = event.position().toPoint()
            self.viewport().setCursor(Qt.CursorShape.ClosedHandCursor)
            return
        if event.button() == Qt.MouseButton.LeftButton:
            element = element_of(self.itemAt(event.position().toPoint()))
            if element is not None:
                self.item_clicked.emit(element.kind, element.element_id)
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event: QMouseEvent) -> None:
        position = event.position().toPoint()
        if self._pan_from is not None:
            delta = position - self._pan_from
            self._pan_from = position
            bar_x, bar_y = self.horizontalScrollBar(), self.verticalScrollBar()
            bar_x.setValue(bar_x.value() - delta.x())
            bar_y.setValue(bar_y.value() - delta.y())
            self.user_moved = True
        scene_point = self.mapToScene(position)
        self.cursor_moved.emit(to_meters(scene_point.x()), to_meters(scene_point.y()))
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event: QMouseEvent) -> None:
        if self._pan_from is not None:
            self._pan_from = None
            self.viewport().unsetCursor()
            return
        super().mouseReleaseEvent(event)

    def leaveEvent(self, event: QEvent) -> None:
        self.cursor_moved.emit(None, None)
        super().leaveEvent(event)

    def keyPressEvent(self, event: QKeyEvent) -> None:
        if event.key() == Qt.Key.Key_Space and not event.isAutoRepeat():
            self._space_down = True
            self.viewport().setCursor(Qt.CursorShape.OpenHandCursor)
        super().keyPressEvent(event)

    def keyReleaseEvent(self, event: QKeyEvent) -> None:
        if event.key() == Qt.Key.Key_Space and not event.isAutoRepeat():
            self._space_down = False
            self.viewport().unsetCursor()
        super().keyReleaseEvent(event)

    def drawForeground(self, painter: QPainter, rect: QRectF | QRect) -> None:
        painter.save()
        painter.resetTransform()
        draw_axis_glyph(painter, self.viewport().rect())
        painter.restore()
