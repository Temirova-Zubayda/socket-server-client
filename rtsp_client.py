#!/usr/bin/env python3
# RTSP viewer for laptop B (tutorial's OpenCV + PyQt5 client). Laptop A must be running rtsp_server.py.
import sys, threading
import cv2
from PyQt5 import QtCore, QtGui, QtWidgets

# Pinky address: give it as an argument, e.g. python3 rtsp_client.py 192.168.4.1
PINKY_IP = sys.argv[1] if len(sys.argv) > 1 else "192.168.129.12"
URL = f"rtsp://{PINKY_IP}:8554/test"
GST = (f"rtspsrc location={URL} latency=0 ! rtph264depay ! h264parse ! avdec_h264 "
       "! videoconvert ! video/x-raw,format=BGR ! appsink drop=true max-buffers=1 sync=false")

class Viewer(QtWidgets.QWidget):
    frame_ready = QtCore.pyqtSignal(QtGui.QImage)

    def __init__(self):
        super().__init__()
        self.setWindowTitle("Pinky camera")
        self.label = QtWidgets.QLabel("Camera off")
        self.label.setAlignment(QtCore.Qt.AlignCenter)
        self.label.setMinimumSize(640, 360)
        on = QtWidgets.QPushButton("Camera On")
        off = QtWidgets.QPushButton("Camera Off")
        on.clicked.connect(self.start)
        off.clicked.connect(self.stop)
        buttons = QtWidgets.QHBoxLayout()
        buttons.addWidget(on)
        buttons.addWidget(off)
        layout = QtWidgets.QVBoxLayout(self)
        layout.addWidget(self.label)
        layout.addLayout(buttons)
        self.frame_ready.connect(lambda img: self.label.setPixmap(QtGui.QPixmap.fromImage(img)))
        self.running = False

    def start(self):
        if not self.running:
            self.running = True
            threading.Thread(target=self.read_loop, daemon=True).start()

    def stop(self):
        self.running = False

    def read_loop(self):
        cap = cv2.VideoCapture(GST, cv2.CAP_GSTREAMER)
        if cap.isOpened():
            print("Using GStreamer (low delay)")
        else:
            print("GStreamer not available in OpenCV, using FFmpeg")
            cap = cv2.VideoCapture(URL)
        while self.running:
            ok, frame = cap.read()
            if not ok:
                print("No frame. Is rtsp_server_pinky.py running on Pinky?")
                break
            rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            h, w, ch = rgb.shape
            img = QtGui.QImage(rgb.data, w, h, ch * w, QtGui.QImage.Format_RGB888).copy()
            self.frame_ready.emit(img.scaled(self.label.width(), self.label.height(), QtCore.Qt.KeepAspectRatio))
        cap.release()
        self.running = False

    def closeEvent(self, event):
        self.stop()
        event.accept()

app = QtWidgets.QApplication(sys.argv)
w = Viewer()
w.show()
sys.exit(app.exec_())
