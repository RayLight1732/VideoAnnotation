from __future__ import annotations
import sys
import cv2
import time
import ffmpeg
import numpy as np
from PyQt5.QtMultimedia import QMediaContent, QMediaPlayer
from PyQt5.QtMultimediaWidgets import QVideoWidget
from PyQt5.QtWidgets import (
    QMainWindow,
    QApplication,
    QWidget,
    QHBoxLayout,
    QVBoxLayout,
    QLabel,
    QPushButton,
    QAction,
    QStyle,
    QFileDialog,
    QSplitter,
)
from PyQt5.QtGui import QIcon, QImage, QPixmap, QPainter, QColor
from PyQt5.QtCore import pyqtSlot, QTimer, Qt, QRect, QDir, QUrl, QSize
from typing import Callable
from GUIProperty import GUIProperty


# https://stackoverflow.com/questions/57842104/how-to-play-videos-in-pyqt
class VideoPlayer(QWidget):
    def __init__(self, interval: int, parent=None):
        super(VideoPlayer, self).__init__(parent)
        # self.setGeometry(300, 50, 400, 350)
        # self.setWindowTitle("MovieAnnotation")
        self.is_playing = False
        self.video: str | None = None
        self.timer = QTimer(self)
        self.interval = interval
        self.mediaPlayer = QMediaPlayer(None, QMediaPlayer.VideoSurface)
        self._initUI()

    def _initUI(self):
        videoWidget = QVideoWidget()
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
        self.playButton.clicked.connect(self.play)

        bottom_widget_layout.addWidget(self.playButton)

        layout = QVBoxLayout()
        layout.addWidget(videoWidget)
        layout.addWidget(bottom_widget, alignment=Qt.AlignHCenter)
        self.setLayout(layout)

        self.mediaPlayer.setVideoOutput(videoWidget)
        self.mediaPlayer.stateChanged.connect(self.mediaStateChanged)
        self.mediaPlayer.positionChanged.connect(self.positionChanged)
        self.mediaPlayer.durationChanged.connect(self.durationChanged)
        self.mediaPlayer.error.connect(self.handleError)

    def abrir(self):
        fileName, _ = QFileDialog.getOpenFileName(
            self,
            "Selecciona los mediose",
            ".",
            "Video Files (*.mp4 *.flv *.ts *.mts *.avi *.wmv)",
        )

        if fileName != "":
            self.mediaPlayer.setMedia(QMediaContent(QUrl.fromLocalFile(fileName)))
            self.playButton.setEnabled(True)
            # self.statusBar.showMessage(fileName)
            self.play()

    def play(self):
        if self.mediaPlayer.state() == QMediaPlayer.PlayingState:
            self.mediaPlayer.pause()
        else:
            self.mediaPlayer.play()

    def mediaStateChanged(self, state):
        if self.mediaPlayer.state() == QMediaPlayer.PlayingState:
            self.playButton.setIcon(self.style().standardIcon(QStyle.SP_MediaPause))
        else:
            self.playButton.setIcon(self.style().standardIcon(QStyle.SP_MediaPlay))

    def positionChanged(self, position):
        # self.positionSlider.setValue(position)
        pass

    def durationChanged(self, duration):
        # self.positionSlider.setRange(0, duration)
        pass

    def setPosition(self, position):
        self.mediaPlayer.setPosition(position)

    def handleError(self):
        self.playButton.setEnabled(False)
        # self.statusBar.showMessage("Error: " + self.mediaPlayer.errorString())


if __name__ == "__main__":
    QMediaContent(
        QUrl.fromLocalFile(
            "C:\\Users\\arusu\\Downloads\\output-Mon18Nov2024175855GMT.mp4"
        )
    )
    app = QApplication(sys.argv)
    w = VideoPlayer(100)
    w.resize(600, 400)
    w.show()
    w.raise_()
    app.exec_()
