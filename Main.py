import sys

from PyQt5.QtCore import *
from PyQt5.QtGui import *
from PyQt5.QtWidgets import *
from enum import Enum


class DragAction(Enum):
    MOVE = 0  # 動画自体を移動
    EDIT_RECT = 1  # 範囲を変更
    CREATE_RECT = 2


class VideoRect:
    def __init__(self, start: float, end: float):
        self.start = start
        self.end = end


class Clip:
    def __init__(self, rect: VideoRect):
        self.rect = rect
        self.danger: list[VideoRect] = []


class MainWindow(QWidget):
    def __init__(self, parent=None):
        super(MainWindow, self).__init__(parent)

        self.setGeometry(300, 50, 400, 350)
        self.setWindowTitle("MovieAnnotation")

        self.horizon = QHBoxLayout()
        self.setLayout(self.horizon)

        self.horizon.addWidget(Widget())


class Widget(QWidget):
    def __init__(self, parent=None):
        super(Widget, self).__init__(parent)
        self.x = 0
        self.setMaximumHeight(200)
        self.dragAction = None
        self.clipRects: list[VideoRect] = []
        self.dangerRects: list[VideoRect] = []
        self.setMouseTracking(True)
        self.isPressed = False

    def isUpper(self, point: QPoint) -> bool:
        return 0 <= point.y() and point.y() <= 100

    def mousePressEvent(self, event):
        if not self.isPressed:
            self.isPressed = True

            self.point: QPoint = event.pos()
            if self.isUpper(self.point):
                self.mousePressOnUpper(event)
            else:
                self.mousePressOnBottom(event)
            self.update()

    def mousePressOnUpper(self, event):
        if event.button() == Qt.LeftButton:
            clickedEdge = self.onClipEdge(self.point)
            if clickedEdge != None:
                clipRect = clickedEdge[0]
                self.targetRect = clipRect
                if clickedEdge[1] == True:
                    self.firstPixel = timeToPixel(clipRect.end)
                else:
                    self.firstPixel = timeToPixel(clipRect.start)
                self.dragAction = DragAction.CREATE_RECT
            else:
                self.dragAction = DragAction.MOVE
        else:
            self.dragAction = DragAction.CREATE_RECT
            self.firstPixel = self.relToAbs(self.point.x())
            self.targetRect = VideoRect(
                pixelToTime(self.firstPixel), pixelToTime(self.firstPixel)
            )
            self.clipRects.append(self.targetRect)

    def mousePressOnBottom(self, event):
        if event.button() == Qt.LeftButton:
            clickedEdge = self.onClipEdge(self.point)
            if clickedEdge != None:
                clipRect = clickedEdge[0]
                self.targetRect = clipRect
                if clickedEdge[1] == True:
                    self.firstPixel = timeToPixel(clipRect.end)
                else:
                    self.firstPixel = timeToPixel(clipRect.start)
                self.dragAction = DragAction.CREATE_RECT
            else:
                self.dragAction = DragAction.MOVE
        else:
            self.dragAction = DragAction.CREATE_RECT
            self.firstPixel = self.relToAbs(self.point.x())
            self.targetRect = VideoRect(
                pixelToTime(self.firstPixel), pixelToTime(self.firstPixel)
            )
            self.clipRects.append(self.targetRect)

    def mouseMoveEvent(self, event):
        pos = event.pos()
        if self.dragAction == DragAction.MOVE:
            self.x += pos.x() - self.point.x()
        elif self.dragAction == DragAction.EDIT_RECT:
            pass
        elif self.dragAction == DragAction.CREATE_RECT:
            absX = self.relToAbs(pos.x())
            self.targetRect.start = pixelToTime(min(absX, self.firstPixel))
            self.targetRect.end = pixelToTime(max(absX, self.firstPixel))
        elif self.isUpper(pos):
            if self.onClipEdge(pos) != None:
                self.setCursor(Qt.CursorShape.SizeHorCursor)
            else:
                self.setCursor(Qt.CursorShape.ArrowCursor)
        self.point = pos

        self.update()

    def mouseReleaseEvent(self, event):
        if self.isPressed:
            self.isPressed = False
            self.dragAction = None
            self.clipRects = mergeClipRect(self.clipRects)
            self.update()

    def paintEvent(self, event):
        self.paintUpper()
        self.paintBottom()

    def paintUpper(self):
        painter = QPainter(self)
        painter.fillRect(self.x, 0, 1000, 100, Qt.yellow)

        painter.setBrush(Qt.red)
        for x in range(0, self.size().width()):
            if (x - self.x) % 10 == 0:
                painter.drawLine(x, 0, x, 100)

        painter.setBrush(Qt.gray)
        for clipRect in self.clipRects:
            startPixel = self.absToRel(timeToPixel(clipRect.start))
            endPixel = self.absToRel(timeToPixel(clipRect.end))
            width = endPixel - startPixel
            painter.drawRect(startPixel, 0, width, 100)

    def paintBottom(self):
        painter = QPainter(self)
        painter.setBrush(Qt.gray)
        for clipRect in self.clipRects:
            startPixel = self.absToRel(timeToPixel(clipRect.start))
            endPixel = self.absToRel(timeToPixel(clipRect.end))
            width = endPixel - startPixel
            painter.drawRect(startPixel, 100, width, 100)

    def onClipEdge(self, point: QPoint) -> tuple[VideoRect, bool] | None:
        for clipRect in self.clipRects:
            start = self.absToRel(timeToPixel(clipRect.start))
            end = self.absToRel(timeToPixel(clipRect.end))
            x = point.x()
            if abs(start - x) < 2:
                return (clipRect, True)
            elif abs(end - x) < 2:
                return (clipRect, False)
        return None

    # 絶対座標から現在のオフセットを勘案した画面上の座標に変換
    def absToRel(self, x: int):
        return x + self.x

    # 画面上の座標から絶対座標に変換
    def relToAbs(self, x: int):
        return x - self.x


def mergeClipRect(clipRects: list[VideoRect]) -> list[VideoRect]:
    sortedList = sorted(clipRects, key=lambda a: a.start)
    result = []
    while len(sortedList) != 0:
        clipRect = sortedList.pop(0)
        start = clipRect.start
        end = clipRect.end

        while True:
            # endがある要素のstartより大きい->交わっている
            # 交わる要素がなくなるまでループ
            edit = False
            for clipRect2 in sortedList:
                if clipRect2.start <= end:
                    edit = True
                    end = max(end, clipRect2.end)
                    sortedList.remove(clipRect2)
                    break
            if edit == False:
                break
        result.append(VideoRect(start, end))
    return result


def pixelToTime(pixel: int) -> float:
    return pixel


def timeToPixel(time: float) -> int:
    return time


def main():
    app = QApplication(sys.argv)
    w = MainWindow()
    w.show()
    w.raise_()
    app.exec_()


if __name__ == "__main__":
    main()
