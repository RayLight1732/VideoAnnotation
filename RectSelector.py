from __future__ import annotations
import sys

from PyQt5.QtCore import *
from PyQt5.QtGui import *
from PyQt5.QtWidgets import *
from enum import Enum
from typing import Callable
import math
from VideoPlayer import VideoPlayer, VideoData
from GUIProperty import GUIProperty
import cv2
from utils import pixelToTime, timeToPixel


class DragAction(Enum):
    MOVE = 0  # 動画自体を移動
    EDIT_RECT = 1  # 範囲を変更
    EDIT_CHILD_RECT = 2


hoverOffset = 3


class VideoRect:
    def __init__(self, start: float, end: float):
        self.start = start
        self.end = end


class RectSelectProcessor:

    def __init__(
        self,
        startTime,
        endTime,
        depth,
        update: Callable[[],],
        xOffset: Callable[[], int],
        setTime: Callable[[float],],
        setCursor: Callable[[any],],
    ):
        self.isPressed = False
        self._videoRect = VideoRect(startTime, endTime)
        self.childProcessors: list[RectSelectProcessor] = []
        self.depth = depth
        self.update = update
        self.xOffset = xOffset
        self.setTime = setTime
        self.setCursor = setCursor
        self.dragAction = None
        self.point = QPoint(0, 0)
        self.can_touch_left = True
        self.can_touch_right = True
        self.targetProcessor = None

    def canTouchLeft(self) -> bool:
        return self.can_touch_left

    def canTouchRight(self) -> bool:
        return self.can_touch_right

    def videoRect(self) -> VideoRect:
        return self._videoRect

    def setVideoRect(self, videoRect: VideoRect):
        self._videoRect = videoRect
        self.update()

    # TODO クリックの開始と終了を一致させる
    def onClick(self, point: QPoint, button):
        if not self.isPressed:
            self.isPressed = True
            self.point: QPoint = point
            if button == Qt.LeftButton:
                clickedEdge = self.onClipEdge(self.point)
                if clickedEdge != None:
                    # 子の領域の端にかぶっていた場合、端の編集を行う
                    childProcesser = clickedEdge[0]
                    self.mouse_target_processor = childProcesser
                    if clickedEdge[1] == True:
                        self.mouse_first_time = childProcesser.videoRect().end
                    else:
                        self.mouse_first_time = childProcesser.videoRect().start
                    self.dragAction = DragAction.EDIT_RECT
                elif self.onRect(self.point) and self.depth == 0:
                    # 子の領域にかぶっており、深さが0なら子に移譲
                    rect = self.onRect(self.point)
                    self.dragAction = DragAction.EDIT_CHILD_RECT
                    self.mouse_target_processor = rect
                    rect.onClick(point, button)
                else:
                    # そうでない(何もない場所をクリック)ときシークバーの移動
                    self.dragAction = DragAction.MOVE
                    self.setTime(pixelToTime(self.relToAbs(point.x())))
        self.update()

    def mouseMoveEvent(self, point: QPoint):
        oldPoint = self.point
        self.point = point
        if self.dragAction == DragAction.MOVE:
            # ドラッグでシークバーを移動
            self.setTime(pixelToTime(self.relToAbs(point.x())))
        elif self.dragAction == DragAction.EDIT_RECT:
            # 領域を編集
            mouse_x = min(self.absToRel(timeToPixel(self._videoRect.end)), point.x())
            mouse_x = max(mouse_x, self.absToRel(self._videoRect.start))
            absX = self.relToAbs(mouse_x)
            start = min(pixelToTime(absX), self.mouse_first_time)
            end = max(pixelToTime(absX), self.mouse_first_time)
            self.mouse_target_processor.setVideoRect(VideoRect(start, end))
            if self.mouse_target_processor == self.targetProcessor:
                self.first_time = pixelToTime(absX)
        elif self.dragAction == DragAction.EDIT_CHILD_RECT:
            # 子に移譲
            self.mouse_target_processor.mouseMoveEvent(point)
        elif self.onClipEdge(point) != None:
            # dragActionがどれにも一致しない→ドラッグしていない
            # そのとき端に触れていたらカーソルを変更
            self.setCursor(Qt.CursorShape.SizeHorCursor)
        else:
            # もし子の領域の上だったらそちらに移譲
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
                self.mouse_target_processor.mouseReleaseEvent(point)
            self.dragAction = None
            self.childProcessors = mergeClipRect(
                self.childProcessors, [self.targetProcessor]
            )
            self.update()

    def onClipEdge(self, point: QPoint) -> tuple[RectSelectProcessor, bool] | None:
        """
        もしも子領域の端に触れていたら、その領域と右か左かを返す
        右ならTrue,左ならFalse
        TODO 定数割り当てたほうがいいかも
        """
        for childProcessor in self.childProcessors:
            childRect = childProcessor.videoRect()
            start = self.absToRel(timeToPixel(childRect.start))
            end = self.absToRel(timeToPixel(childRect.end))
            x = point.x()
            if abs(x - start) < hoverOffset and childProcessor.canTouchLeft():
                return (childProcessor, True)
            elif abs(end - x) < hoverOffset and childProcessor.canTouchRight():
                return (childProcessor, False)
        return None

    def onButtonStateChanged(self, pressed, button_depth):
        print(pressed)
        if button_depth == 0:
            if pressed:
                self.first_time = self.seek_bar_pos
                newProcessor = RectSelectProcessor(
                    self.first_time,
                    self.first_time,
                    self.depth + 1,
                    self.update,
                    self.xOffset,
                    self.setTime,
                    self.setCursor,
                )
                newProcessor.can_touch_right = False
                self.childProcessors.append(newProcessor)
                self.targetProcessor = newProcessor
            else:
                if self.targetProcessor:
                    self.targetProcessor.can_touch_right = True
                    self.targetProcessor.can_touch_left = True
                    self.targetProcessor = None
                self.childProcessors = mergeClipRect(self.childProcessors)
        elif self.targetProcessor:
            self.targetProcessor.onButtonStateChanged(pressed, button_depth - 1)

    def onSeekbarChanged(self, pos):
        """
        :param pos: time
        """
        self.seek_bar_pos = pos
        if self.targetProcessor:
            start = min(pos, self.first_time)
            end = max(pos, self.first_time)
            if start == pos:
                self.targetProcessor.can_touch_left = False
                self.targetProcessor.can_touch_right = False
            else:
                self.targetProcessor.can_touch_left = False
                self.targetProcessor.can_touch_right = False
            self.targetProcessor.setVideoRect(VideoRect(start, end))

        for child in self.childProcessors:
            child.onSeekbarChanged(pos)

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
        time: GUIProperty,
        x_offset: GUIProperty,
        video_data: GUIProperty,
        parent=None,
    ):
        super(RectSelectWidget, self).__init__(parent)
        self.x_offset = x_offset
        self.time = time
        self.time.addListener(self, self.onTimeChanged)
        self.time.setValueConverter(self.__valueConverter)
        self.setMouseTracking(True)
        self.video_data = video_data
        self.parentProcessor = None

    def onButtonStateChanged(self, pressed, button_depth):
        # 移動できるといい
        # created by的なフラグをVideoRectに用意する
        if 0 <= button_depth <= 1:
            self.parentProcessor.onButtonStateChanged(pressed, button_depth)
        else:
            # err
            pass

    def __valueConverter(self, value):
        if self.video_data.getValue():
            return min(max(0, value), self.video_data.getValue().getVideoLength())
        else:
            return value

    def onTimeChanged(self, source, value):

        if not self.isInScreen(value):
            self.x_offset.setValue(self, timeToPixel(value))
        if self.parentProcessor:
            self.parentProcessor.onSeekbarChanged(value)
        self.update()

    def isInScreen(self, time):
        """
        指定された時間がスクリーン上にあるかどうかを判定する
        """
        pix = self.absToRel(timeToPixel(time))
        return 0 <= pix <= self.width()

    def mousePressEvent(self, event):
        if self.parentProcessor:
            self.parentProcessor.onClick(event.pos(), event.button())

    def mouseMoveEvent(self, event):
        if self.parentProcessor:
            self.parentProcessor.mouseMoveEvent(event.pos())

    def mouseReleaseEvent(self, event):
        if self.parentProcessor:
            self.parentProcessor.mouseReleaseEvent(event.pos())

    def paintEvent(self, event):
        painter = QPainter(self)
        if self.parentProcessor:
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
            if (x - self.x_offset.getValue()) % 10 == 0:
                painter.drawLine(x, 0, x, self.height())
        if self.parentProcessor:
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

        time_bar = self.absToRel(timeToPixel(self.time.getValue()))

        painter.fillRect(time_bar - 1, 0, 3, self.height(), Qt.blue)

    # 絶対座標から現在のオフセットを勘案した画面上の座標に変換
    def absToRel(self, x: int):
        return x + self.x_offset.getValue()

    # 画面上の座標から絶対座標に変換
    def relToAbs(self, x: int):
        return x - self.x_offset.getValue()

    def onVideoChanged(self, video_length: float | None):
        if video_length:
            self.parentProcessor = RectSelectProcessor(
                0,
                video_length,
                0,
                self.update,
                self.x_offset.getValue,
                lambda value: self.time.setValue(self, value),
                self.setCursor,
            )

        else:
            self.parentProcessor = None
        self.update()

    def getExportObject(self) -> dict:
        return toExportObject(self.parentProcessor)


def mergeClipRect(
    clipRects: list[RectSelectProcessor], ignores: list[RectSelectProcessor] = []
) -> list[RectSelectProcessor]:
    sortedList = sorted(clipRects, key=lambda a: a.videoRect().start)
    sortedList = [a for a in sortedList if not a in ignores and a != None]
    result = [a for a in ignores if a != None]
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
            clipRect.setTime,
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


def toExportObject(processor: RectSelectProcessor) -> dict:
    result = {}
    result["start"] = processor.videoRect().start
    result["end"] = processor.videoRect().end
    children = list(map(toExportObject, processor.childProcessors))
    result["children"] = children
    return result
