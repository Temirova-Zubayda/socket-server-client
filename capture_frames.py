#!/usr/bin/env python3
# Laptop B: Pinky stream + frame saving for YOLO dataset.
import os, sys, threading, time
import cv2
from PyQt5 import QtCore, QtGui, QtWidgets

# Pinky address: give it as an argument, e.g. python3 capture_frames.py 192.168.4.1
PINKY_IP = sys.argv[1] if len(sys.argv) > 1 else "192.168.129.12"
URL = f"rtsp://{PINKY_IP}:8554/test"
GST = (f"rtspsrc location={URL} latency=0 ! rtph264depay ! h264parse ! avdec_h264 "
       "! videoconvert ! video/x-raw,format=BGR ! appsink drop=true max-buffers=1 sync=false")
SAVE_DIR = os.path.expanduser("~/networking/dataset/images")
EVERY_N = 15   # auto save: 1 frame out of 15 (30 fps -> 2 images per second)

class Viewer(QtWidgets.QWidget):
    frame_ready = QtCore.pyqtSignal(QtGui.QImage)
    count_changed = QtCore.pyqtSignal(int)

    def __init__(self):
        super().__init__()
        os.makedirs(SAVE_DIR, exist_ok=True)
        self.setWindowTitle("Pinky camera - capture")
        self.label = QtWidgets.QLabel("Camera off")
        self.label.setAlignment(QtCore.Qt.AlignCenter)
        self.label.setMinimumSize(640, 360)
        self.info = QtWidgets.QLabel()
        on = QtWidgets.QPushButton("Camera On")
        off = QtWidgets.QPushButton("Camera Off")
        save = QtWidgets.QPushButton("Save frame")
        self.auto = QtWidgets.QPushButton("Auto save")
        self.auto.setCheckable(True)
        on.clicked.connect(self.start)
        off.clicked.connect(self.stop)
        save.clicked.connect(self.save_one)
        buttons = QtWidgets.QHBoxLayout()
        for b in (on, off, save, self.auto):
            buttons.addWidget(b)
        layout = QtWidgets.QVBoxLayout(self)
        layout.addWidget(self.label)
        layout.addWidget(self.info)
        layout.addLayout(buttons)
        self.frame_ready.connect(lambda img: self.label.setPixmap(QtGui.QPixmap.fromImage(img)))
        self.count_changed.connect(lambda n: self.info.setText(f"Saved: {n}  ->  {SAVE_DIR}"))
        self.running = False
        self.last = None
        self.saved = len([f for f in os.listdir(SAVE_DIR) if f.endswith(".jpg")])
        self.count_changed.emit(self.saved)

    def start(self):
        if not self.running:
            self.running = True
            threading.Thread(target=self.read_loop, daemon=True).start()

    def stop(self):
        self.running = False

    def write(self, frame):
        name = time.strftime("%Y%m%d_%H%M%S_") + f"{int(time.time() * 1000) % 1000:03d}.jpg"
        cv2.imwrite(os.path.join(SAVE_DIR, name), frame)
        self.saved += 1
        self.count_changed.emit(self.saved)

    def save_one(self):
        if self.last is not None:
            self.write(self.last.copy())

    def read_loop(self):
        cap = cv2.VideoCapture(GST, cv2.CAP_GSTREAMER)
        if not cap.isOpened():
            print("GStreamer not available in OpenCV, using FFmpeg")
            cap = cv2.VideoCapture(URL)
        n = 0
        while self.running:
            ok, frame = cap.read()
            if not ok:
                print("No frame. Is rtsp_server_pinky.py running on Pinky?")
                break
            self.last = frame
            n += 1
            if self.auto.isChecked() and n % EVERY_N == 0:
                self.write(frame)
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
