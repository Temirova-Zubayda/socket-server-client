#!/usr/bin/env python3
# Big millisecond clock for measuring stream delay. Run on laptop B.
import sys, time
from PyQt5 import QtCore, QtGui, QtWidgets

app = QtWidgets.QApplication(sys.argv)
label = QtWidgets.QLabel()
label.setWindowTitle("Clock")
label.setAlignment(QtCore.Qt.AlignCenter)
label.setFont(QtGui.QFont("Monospace", 64, QtGui.QFont.Bold))
label.setStyleSheet("background: black; color: white; padding: 20px;")

def tick():
    t = time.time()
    label.setText(time.strftime("%H:%M:%S", time.localtime(t)) + f".{int(t * 1000) % 1000:03d}")

timer = QtCore.QTimer()
timer.timeout.connect(tick)
timer.start(1)
tick()
label.show()
sys.exit(app.exec_())
