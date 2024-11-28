import sys
import cv2
from PyQt5.QtMultimedia import QMediaContent
from PyQt5.QtWidgets import (
    QApplication,
    QWidget,
    QHBoxLayout,
    QVBoxLayout,
    QPushButton,
    QStyle,
    QSlider,
)
from PyQt5.QtGui import QImage, QPainter
from PyQt5.QtCore import QTimer, Qt, QRect, QUrl, QSize
from gui_property import GUIProperty


class ImageRenderer(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.image: QImage | None = None

    def paintEvent(self, event):
        painter = QPainter(self)
        w = self.width()
        h = self.height()
        painter.fillRect(0, 0, w, h, Qt.black)
        if self.image:
            iw = self.image.width()
            ih = self.image.height()

            ratio = min(w / iw, h / ih)
            targetW = int(ratio * iw)
            targetH = int(ratio * ih)
            aleft = int((w - targetW) / 2)
            atop = int((h - targetH) / 2)
            targetRect = QRect(aleft, atop, targetW, targetH)
            sourceRect = QRect(0, 0, iw, ih)
            painter.drawImage(targetRect, self.image, sourceRect)

        painter.end()

    def setImage(self, image: QImage | None):
        self.image = image
        self.update()


class VideoData:
    def __init__(self, fps=None, frame_count=None):
        self.fps = fps
        self.frame_count = frame_count

    def getFPS(self) -> int | None:
        return self.fps

    def getFrameCount(self) -> int | None:
        return self.frame_count

    def getVideoLength(self) -> float | None:
        if self.fps and self.frame_count:
            return self.frame_count / self.fps
        else:
            return None


class VideoPlayer(QWidget):
    def __init__(self, time: GUIProperty, video_data: GUIProperty, parent=None):
        """
        :param time: 動画の時間(float)
        :param video_data: 動画の情報 VideoData|None型
        :param video_length: ビデオの再生時間 float|None

        """
        super(VideoPlayer, self).__init__(parent)
        self.playSpeed = 1  # 倍率(整数倍)
        self.time = time
        self.time.addListener(self, self.onTimeChange)
        self.is_playing = False
        self.video: cv2.VideoCapture | None = None
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.__onInterval)
        self.curret_frame = 0
        self.video_data = video_data
        self._initUI()

    def _initUI(self):
        self.image_renderer = ImageRenderer()
        bottom_widget = QWidget()
        bottom_widget.setMaximumHeight(25)
        bottom_widget_layout = QHBoxLayout(bottom_widget)
        bottom_widget_layout.setContentsMargins(0, 0, 0, 0)

        btnSize = QSize(16, 16)
        self.playButton = QPushButton()
        self.playButton.setEnabled(False)
        self.playButton.setFixedHeight(24)
        self.playButton.setIconSize(btnSize)
        self.playButton.setIcon(self.style().standardIcon(QStyle.SP_MediaPlay))
        self.playButton.clicked.connect(self.flipPlayStatus)

        slider = QSlider(Qt.Orientation.Horizontal)

        slider.setMinimum(1)
        slider.setMaximum(5)
        slider.valueChanged.connect(self.setPlaySpeed)
        bottom_widget_layout.addWidget(self.playButton)
        bottom_widget_layout.addWidget(slider)

        layout = QVBoxLayout()
        layout.addWidget(self.image_renderer)
        layout.addWidget(bottom_widget, alignment=Qt.AlignHCenter)
        self.setLayout(layout)

    def setPlaySpeed(self, speed):
        self.playSpeed = speed

    def onTimeChange(self, source, value: float):
        if source != self:
            newTime = min(self.video_data.getValue().getVideoLength(), value)
            self.__setCurrentFrame(int(newTime * self.video_data.getValue().getFPS()))

    def playVideo(self):
        if (
            not self.isPlaying()
            and self.video
            and self.curret_frame < self.video_data.getValue().getFrameCount()
        ):
            self.is_playing = True
            self.timer.setInterval(int(1000 / self.video_data.getValue().getFPS()))
            self.timer.start()
            self.playButton.setIcon(self.style().standardIcon(QStyle.SP_MediaPause))

    def stopVideo(self):
        if self.isPlaying():
            self.timer.stop()
            self.is_playing = False
            self.playButton.setIcon(self.style().standardIcon(QStyle.SP_MediaPlay))

    def flipPlayStatus(self):
        if self.isPlaying():
            self.stopVideo()
        else:
            self.playVideo()

    def isPlaying(self) -> bool:
        return self.is_playing

    def setVideo(self, video: cv2.VideoCapture) -> float | None:
        """
        :return: 動画の長さ(秒)
        """
        self.stopVideo()
        self.video = video
        if video:
            self.video_width = int(video.get(cv2.CAP_PROP_FRAME_WIDTH))
            self.video_height = int(video.get(cv2.CAP_PROP_FRAME_HEIGHT))
            fps = int(video.get(cv2.CAP_PROP_FPS))
            frame_count = int(video.get(cv2.CAP_PROP_FRAME_COUNT))
            self.video_data.setValue(self, VideoData(fps, frame_count))
            self.time.setValue(None, 0)
            self.playButton.setEnabled(True)
            return self.video_data.getValue().getVideoLength()
        else:
            self.playButton.setEnabled(False)
            self.video_data.setValue(self, None)
            return None

    def getCurrentTime(self):
        return self.curret_frame / self.video_data.getValue().getFPS()

    def __incrementCurrentFrame(self):
        for _ in range(0, self.playSpeed - 1):
            self.curret_frame += 1
            self.updateImage(True)
        self.curret_frame += 1
        self.time.setValue(self, self.getCurrentTime())
        isEnd = self.updateImage()
        if isEnd:
            self.stopVideo()

    def __setCurrentFrame(self, frame):
        self.curret_frame = frame
        self.time.setValue(self, self.getCurrentTime())
        if self.video:
            self.video.set(cv2.CAP_PROP_POS_FRAMES, self.curret_frame)
            isEnd = self.updateImage()
            if isEnd:
                self.stopVideo()

    def __getCurretnFrame(self):
        return self.curret_frame

    def __onInterval(self):
        self.__incrementCurrentFrame()

    def updateImage(self, only_increment_frame=False) -> bool:
        """
        :return: 終わったらtrue それ以外(videoがない場合も含む)はfalse
        """
        if self.video:
            ret, frame = self.video.read()
            if ret and not only_increment_frame:
                rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB).data
                image = QImage(
                    rgb,
                    self.video_width,
                    self.video_height,
                    self.video_width * 3,
                    QImage.Format_RGB888,
                )
                self.image_renderer.setImage(image)
                return False
            else:
                self.image_renderer.setImage(None)
                return True
        else:
            self.image_renderer.setImage(None)
            return False


if __name__ == "__main__":
    QMediaContent(
        QUrl.fromLocalFile(
            "C:\\Users\\arusu\\Downloads\\output-Mon18Nov2024175855GMT.mp4"
        )
    )
    app = QApplication(sys.argv)
    w = VideoPlayer(GUIProperty((0, False)), GUIProperty(0))
    w.setVideo(
        cv2.VideoCapture(
            "C:\\Users\\arusu\\Downloads\\output-Mon18Nov2024175855GMT.mp4"
        )
    )
    w.resize(600, 400)
    w.show()
    w.raise_()
    app.exec_()
