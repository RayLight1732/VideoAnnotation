from __future__ import annotations
import sys

from PyQt5.QtCore import *
from PyQt5.QtGui import *
from PyQt5.QtWidgets import *
from enum import Enum
from typing import Callable
import math


class DragAction(Enum):
    MOVE = 0  # 動画自体を移動
    EDIT_RECT = 1  # 範囲を変更
    CREATE_RECT = 2
    EDIT_CHILD_RECT = 3


hoverOffset = 3


class VideoRect:
    def __init__(self, start: float, end: float):
        self.start = start
        self.end = end


class MainWindow(QMainWindow):
    def __init__(self, parent=None):
        super(MainWindow, self).__init__(parent)

        self.setGeometry(300, 50, 400, 350)
        self.setWindowTitle("MovieAnnotation")

        # QSplitterの作成
        splitter = QSplitter(Qt.Vertical)  # 水平方向に分割
        text_edit1 = QTextEdit("Left Widget")
        rect_selector = RectSelectWidget(1000)

        splitter.addWidget(text_edit1)
        splitter.addWidget(rect_selector)
        splitter.setSizes([300, 100])

        # レイアウトに追加
        layout = QVBoxLayout()
        layout.addWidget(splitter)

        container = QWidget()
        container.setLayout(layout)

        self.setCentralWidget(container)


class RectSelectProcessor:

    def __init__(
        self,
        startTime,
        endTime,
        depth,
        update: Callable[[],],
        xOffset: Callable[[], int],
        setXOffset: Callable[[int],],
        setCursor: Callable[[any],],
    ):
        self.isPressed = False
        self._videoRect = VideoRect(startTime, endTime)
        self.childProcessors: list[RectSelectProcessor] = []
        self.depth = depth
        self.update = update
        self.xOffset = xOffset
        self.setXOffset = setXOffset
        self.setCursor = setCursor
        self.dragAction = None
        self.point = QPoint(0, 0)

    def videoRect(self) -> VideoRect:
        return self._videoRect

    def setVideoRect(self, videoRect: VideoRect):
        self._videoRect = videoRect
        self.update()

    def onClick(self, point: QPoint, button):
        if not self.isPressed:
            self.isPressed = True
            self.point: QPoint = point
            print(button)
            if button == Qt.LeftButton:
                clickedEdge = self.onClipEdge(self.point)
                if clickedEdge != None:
                    childProcesser = clickedEdge[0]
                    self.targetProcessor = childProcesser
                    if clickedEdge[1] == True:
                        self.firstPixel = timeToPixel(childProcesser.videoRect().end)
                    else:
                        self.firstPixel = timeToPixel(childProcesser.videoRect().start)
                    self.dragAction = DragAction.CREATE_RECT
                else:
                    if self.onRect(self.point) and self.depth <= 0:
                        rect = self.onRect(self.point)
                        self.dragAction = DragAction.EDIT_CHILD_RECT
                        self.targetProcessor = rect
                        rect.onClick(point, button)
                    else:
                        self.dragAction = DragAction.MOVE
            elif self.onRect(self.point) and self.depth <= 0:
                rect = self.onRect(self.point)
                self.dragAction = DragAction.EDIT_CHILD_RECT
                self.targetProcessor = rect
                rect.onClick(point, button)
            elif self.isInParentRect(self.point.x()):
                self.dragAction = DragAction.CREATE_RECT
                self.firstPixel = self.relToAbs(self.point.x())
                startTime = pixelToTime(self.firstPixel)
                endTime = pixelToTime(self.firstPixel)
                newProcessor = RectSelectProcessor(
                    startTime,
                    endTime,
                    self.depth + 1,
                    self.update,
                    self.xOffset,
                    self.setXOffset,
                    self.setCursor,
                )
                self.childProcessors.append(newProcessor)
                self.targetProcessor = newProcessor

        self.update()

    def mouseMoveEvent(self, point: QPoint):
        oldPoint = self.point
        self.point = point
        if self.dragAction == DragAction.MOVE:
            self.setXOffset(self.xOffset() + point.x() - oldPoint.x())
        elif self.dragAction == DragAction.EDIT_RECT:
            pass
        elif self.dragAction == DragAction.CREATE_RECT:
            mouse_x = min(self.absToRel(timeToPixel(self._videoRect.end)), point.x())
            mouse_x = max(mouse_x, self.absToRel(self._videoRect.start))
            absX = self.relToAbs(mouse_x)
            start = pixelToTime(min(absX, self.firstPixel))
            end = pixelToTime(max(absX, self.firstPixel))
            self.targetProcessor.setVideoRect(VideoRect(start, end))
        elif self.dragAction == DragAction.EDIT_CHILD_RECT:
            self.targetProcessor.mouseMoveEvent(point)
        elif self.onClipEdge(point) != None:
            self.setCursor(Qt.CursorShape.SizeHorCursor)
        else:
            rect = self.onRect(self.point)
            if rect != None:
                rect.mouseMoveEvent(point)
            else:
                self.setCursor(Qt.CursorShape.ArrowCursor)

        self.update()

    def mouseReleaseEvent(self, point: QPoint):
        if self.isPressed:
            self.isPressed = False
            if self.dragAction == DragAction.EDIT_CHILD_RECT:
                self.targetProcessor.mouseReleaseEvent(point)
            self.dragAction = None
            self.childProcessors = mergeClipRect(self.childProcessors)
            self.update()

    def onClipEdge(self, point: QPoint) -> tuple[RectSelectProcessor, bool] | None:
        for childProcessor in self.childProcessors:
            childRect = childProcessor.videoRect()
            start = self.absToRel(timeToPixel(childRect.start))
            end = self.absToRel(timeToPixel(childRect.end))
            x = point.x()
            if -hoverOffset <= x - start < hoverOffset:
                return (childProcessor, True)
            elif -hoverOffset <= end - x < hoverOffset:
                return (childProcessor, False)
        return None

    def onRect(self, point: QPoint) -> RectSelectProcessor | None:
        for childProcessor in self.childProcessors:
            rect = childProcessor.videoRect()
            start = self.absToRel(timeToPixel(rect.start))
            end = self.absToRel(timeToPixel(rect.end))
            if start + hoverOffset <= point.x() <= end + hoverOffset:
                return childProcessor
        return None

    # 絶対座標から現在のオフセットを勘案した画面上の座標に変換
    def absToRel(self, x: int):
        return x + self.xOffset()

    # 画面上の座標から絶対座標に変換
    def relToAbs(self, x: int):
        return x - self.xOffset()

    def isInParentRect(self, x: int):
        return self.absToRel(
            timeToPixel(self._videoRect.start)
        ) <= x and x <= self.absToRel(timeToPixel(self._videoRect.end))


class RectSelectWidget(QWidget):
    def __init__(
        self,
        length,
        parent=None,
    ):
        super(RectSelectWidget, self).__init__(parent)
        self.x_offset = 0
        self.setMouseTracking(True)
        self.parentProcessor = RectSelectProcessor(
            0,
            length,
            0,
            self.update,
            lambda: self.x_offset,
            self.setXOffset,
            self.setCursor,
        )

    def setXOffset(self, xOffset: int):
        self.x_offset = xOffset

    def mousePressEvent(self, event):
        self.parentProcessor.onClick(event.pos(), event.button())

    def mouseMoveEvent(self, event):
        self.parentProcessor.mouseMoveEvent(event.pos())

    def mouseReleaseEvent(self, event):
        self.parentProcessor.mouseReleaseEvent(event.pos())

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.begin(self)
        parentRect = self.parentProcessor.videoRect()
        parentStartTime = parentRect.start
        parentEndTime = parentRect.end
        parentStartPixel = self.absToRel(timeToPixel(parentStartTime))
        parentEndPixel = self.absToRel(timeToPixel(parentEndTime))
        painter.fillRect(
            parentStartPixel,
            0,
            parentEndPixel - parentStartPixel,
            self.height(),
            Qt.yellow,
        )

        painter.setBrush(Qt.red)
        for x in range(0, self.size().width()):
            if (x - self.x_offset) % 10 == 0:
                painter.drawLine(x, 0, x, self.height())

        for childProcessor in self.parentProcessor.childProcessors:
            painter.setBrush(Qt.gray)
            childRect = childProcessor.videoRect()
            startPixel = self.absToRel(timeToPixel(childRect.start))
            endPixel = self.absToRel(timeToPixel(childRect.end))
            width = endPixel - startPixel
            painter.drawRect(startPixel, 0, width, self.height())
            painter.setBrush(Qt.red)
            for childProcessor in childProcessor.childProcessors:
                childRect = childProcessor.videoRect()
                startPixel = self.absToRel(timeToPixel(childRect.start))
                endPixel = self.absToRel(timeToPixel(childRect.end))
                width = endPixel - startPixel
                painter.drawRect(startPixel, 0, width, self.height())

        painter.end()

    # 絶対座標から現在のオフセットを勘案した画面上の座標に変換
    def absToRel(self, x: int):
        return x + self.x_offset

    # 画面上の座標から絶対座標に変換
    def relToAbs(self, x: int):
        return x - self.x_offset


class ValidRectSelectWidget(RectSelectWidget):
    def __init__(self, parent=None, start_x=0, parent_width=0):
        super(ValidRectSelectWidget, self).__init__(parent, start_x, parent_width)


def mergeClipRect(clipRects: list[RectSelectProcessor]) -> list[RectSelectProcessor]:
    sortedList = sorted(clipRects, key=lambda a: a.videoRect().start)
    result = []
    while len(sortedList) != 0:
        clipRect = sortedList.pop(0)
        start = clipRect.videoRect().start
        end = clipRect.videoRect().end
        childPrecessors = list(clipRect.childProcessors)
        while True:
            # endがある要素のstartより大きい->交わっている
            # 交わる要素がなくなるまでループ
            edit = False
            for clipRect2 in sortedList:
                if clipRect2.videoRect().start <= end:
                    edit = True
                    end = max(end, clipRect2.videoRect().end)
                    sortedList.remove(clipRect2)
                    childPrecessors += clipRect2.childProcessors
                    break
            if edit == False:
                break
        newProcessor = RectSelectProcessor(
            start,
            end,
            clipRect.depth,
            clipRect.update,
            clipRect.xOffset,
            clipRect.setXOffset,
            clipRect.setCursor,
        )
        newProcessor.childProcessors = mergeClipRect(childPrecessors)
        clipChild(newProcessor)

        result.append(newProcessor)
    return result


def clipChild(processor: RectSelectProcessor):
    newChildren = []
    parentRect = processor.videoRect()
    for child in processor.childProcessors:
        childRect = child.videoRect()
        newStart = max(childRect.start, parentRect.start)
        newEnd = min(childRect.end, parentRect.end)
        if newStart < newEnd:
            child.videoRect().start = newStart
            child.videoRect().end = newEnd
            newChildren.append(child)
    processor.childProcessors = newChildren


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
