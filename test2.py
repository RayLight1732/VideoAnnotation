import cv2
import numpy as np
import sys
from PyQt5 import QtWidgets, QtCore, QtGui


# https://ymt-lab.com/post/2020/pyqt5-opencv-play-video/
class MainWindow(QtWidgets.QMainWindow):
    def __init__(self):
        super().__init__()

        self.resize(800, 600)
        self.centralwidget = QtWidgets.QWidget(self)
        self.graphicsView = QtWidgets.QGraphicsView(self.centralwidget)
        self.horizontalSlider = QtWidgets.QSlider(self.centralwidget)
        self.horizontalSlider.setOrientation(QtCore.Qt.Horizontal)
        self.verticalLayout = QtWidgets.QVBoxLayout(self.centralwidget)
        self.verticalLayout.setSpacing(0)
        self.verticalLayout.setContentsMargins(0, 0, 0, 0)
        self.verticalLayout.addWidget(self.graphicsView)
        self.verticalLayout.addWidget(self.horizontalSlider)
        self.setCentralWidget(self.centralwidget)

        self.time_line = QtCore.QTimeLine()
        self.time_line.valueChanged.connect(self.draw_frame)
        self.time_line.finished.connect(self.stop_video)

        self.video = cv2.VideoCapture(
            "C:\\Users\\arusu\\Downloads\\output-Mon18Nov2024175855GMT.mp4"
        )
        self.start_video()

    def start_video(self):
        frame_rate = self.video.get(cv2.CAP_PROP_FPS)
        frame_count = self.video.get(cv2.CAP_PROP_FRAME_COUNT)
        frame_time = 1000 / frame_rate
        video_time = frame_count / frame_rate * 1000
        self.video_width = int(self.video.get(cv2.CAP_PROP_FRAME_WIDTH))
        self.video_height = int(self.video.get(cv2.CAP_PROP_FRAME_HEIGHT))

        self.horizontalSlider.setMaximum(int(frame_count))
        self.graphicsView.setScene(
            QtWidgets.QGraphicsScene(
                0, 0, self.video_width, self.video_height, self.graphicsView
            )
        )

        self.time_line.setDuration(int(video_time))
        self.time_line.setUpdateInterval(int(frame_time))
        self.time_line.start()

    def stop_video(self):
        self.video.release()

    def draw_frame(self):
        ret, frame = self.video.read()
        if ret:
            rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB).data
            image = QtGui.QImage(
                rgb,
                self.video_width,
                self.video_height,
                self.video_width * 3,
                QtGui.QImage.Format_RGB888,
            )
            pixmap = QtGui.QPixmap.fromImage(image)
            self.graphicsView.scene().clear()
            self.graphicsView.scene().addPixmap(pixmap)
        self.horizontalSlider.setValue(self.horizontalSlider.value() + 1)


def main():
    app = QtWidgets.QApplication(sys.argv)
    window = MainWindow()
    window.show()
    app.exec()


if __name__ == "__main__":
    main()
