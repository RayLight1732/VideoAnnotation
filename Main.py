from __future__ import annotations
import sys

from PyQt5.QtCore import *
from PyQt5.QtGui import *
from PyQt5.QtWidgets import *
from video_player import VideoPlayer
from gui_property import GUIProperty
import cv2
from utils import pixelToTime, timeToPixel
from rect_selector import RectSelectWidget
import json
import os


class MainWindow(QMainWindow):
    def __init__(self, parent=None):
        super(MainWindow, self).__init__(parent)

        self.setGeometry(300, 50, 400, 350)
        self.setWindowTitle("MovieAnnotation")
        self._video_path = ""
        menubar = self.menuBar()
        filemenu = menubar.addMenu("&File")

        self._open_act = QAction("開く")
        self._open_act.setShortcut("Ctrl+O")  # shortcut
        self._open_act.triggered.connect(self.openVideo)  # open_actとメソッドを紐づける
        filemenu.addAction(self._open_act)

        self._save_act = QAction("保存")
        self._save_act.setShortcut("Ctrl+S")
        self._save_act.setEnabled(False)
        self._save_act.triggered.connect(self.save)
        filemenu.addAction(self._save_act)

        # QSplitterの作成
        splitter = QSplitter(Qt.Vertical)  # 水平方向に分割
        splitter_palette = splitter.palette()
        splitter_palette.setColor(QPalette.ColorRole.Window, QColor("black"))
        splitter.setPalette(splitter_palette)

        time = GUIProperty(0)
        self._x_offset = GUIProperty(0)
        self._x_offset.addListener(self, self.onXOffsetChanged)
        self.video_data = GUIProperty(None)
        self.video_data.addListener(self, self.onVideoDataChanged)
        self.video_player = VideoPlayer(time, self.video_data)

        self._valid_button_pressed = False
        self._danger_button_pressed = False
        button_widget_layout = QHBoxLayout()

        self._valid_area_button = QPushButton()
        self._valid_area_button.setText("有効")
        self._valid_area_button.clicked.connect(self.onValidButtonClicked)
        self.setValidButtonEnabled(False)
        button_widget_layout.addWidget(self._valid_area_button)

        self._danger_area_button = QPushButton()
        self._danger_area_button.setText("危険")
        self._danger_area_button.clicked.connect(self.onDangerButtonClicked)
        self.setDangerButtonEnabled(False)
        button_widget_layout.addWidget(self._danger_area_button)

        top_widget = QWidget()
        top_widget_layout = QVBoxLayout(top_widget)
        top_widget_layout.addWidget(self.video_player)
        top_widget_layout.addLayout(button_widget_layout)

        bottom_widget = QWidget()
        bottom_widget_layout = QVBoxLayout(bottom_widget)
        self.rect_selector = RectSelectWidget(time, self._x_offset, self.video_data)
        self._slider = QSlider(Qt.Orientation.Horizontal)
        self._slider.setEnabled(False)
        self._slider.valueChanged.connect(self.onSliderPositionChanged)

        bottom_widget_layout.addWidget(self.rect_selector)
        bottom_widget_layout.addWidget(self._slider)

        splitter.addWidget(top_widget)
        splitter.addWidget(bottom_widget)
        splitter.setSizes([300, 100])

        # レイアウトに追加
        layout = QVBoxLayout()
        layout.addWidget(splitter)

        container = QWidget()
        container.setLayout(layout)

        self.setCentralWidget(container)

    def onValidButtonClicked(self):
        self._valid_button_pressed = not self._valid_button_pressed
        self.setDangerButtonEnabled(self._valid_button_pressed)
        self.rect_selector.onButtonStateChanged(self._valid_button_pressed, 0)

    def onDangerButtonClicked(self):
        self._danger_button_pressed = not self._danger_button_pressed
        self.rect_selector.onButtonStateChanged(self._danger_button_pressed, 1)

    def setDangerButtonEnabled(self, enabled: bool):
        self._danger_area_button.setEnabled(enabled)
        if not enabled and self._danger_button_pressed:
            self._danger_button_pressed = False
            self.rect_selector.onButtonStateChanged(False, 1)

    def setValidButtonEnabled(self, enabled: bool):
        self._valid_area_button.setEnabled(enabled)

    def openVideo(self):
        fileName, _ = QFileDialog.getOpenFileName(
            self,
            "Selecciona los mediose",
            ".",
            "Video Files (*.mp4 *.flv *.ts *.mts *.avi *.wmv)",
        )

        if fileName != "":
            self.setVideoPath(fileName)

    def save(self):
        if self._video_path != "":
            base = os.path.splitext(self._video_path)[0]  # 拡張子を除いた部分を取得
            new_path = f"{base}.txt"  # 新しい拡張子を追加
            f = open(new_path, "w")
            export_object = self.rect_selector.getExportObject()
            text = json.dumps(export_object)
            f.write(text)
            f.close()

    def setVideoPath(self, path):
        self._video_path = path
        video = cv2.VideoCapture(path)
        length = self.video_player.setVideo(video)
        self.rect_selector.onVideoChanged(length)

    def onVideoDataChanged(self, source, value):
        if value == None:
            self._slider.setEnabled(False)
            self.setValidButtonEnabled(False)
            self._save_act.setEnabled(False)
        else:
            self._slider.setMinimum(0)
            self._slider.setMaximum(value.getFrameCount())
            self._slider.setEnabled(True)
            self.setValidButtonEnabled(True)
            self._save_act.setEnabled(True)

    def onSliderPositionChanged(self, frame):
        video_data = self.video_data.getValue()
        if video_data:
            self._x_offset.setValue(self, -1 * timeToPixel(frame / video_data.getFPS()))
            self.update()

    def onXOffsetChanged(self, source, value):
        video_data = self.video_data.getValue()
        if source != self and video_data:
            frame = int(pixelToTime(value) * video_data.getFPS())
            self._slider.setValue(frame)
            self.update()


def main():
    app = QApplication(sys.argv)
    w = MainWindow()
    # w.setVideoPath("C:\\Users\\arusu\\Downloads\\output-Mon18Nov2024175855GMT.mp4")
    w.show()
    w.raise_()
    app.exec_()


if __name__ == "__main__":
    main()
