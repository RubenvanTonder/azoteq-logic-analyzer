import sys
import subprocess
import numpy as np
import pyqtgraph as pg
from PyQt6.QtWidgets import (QApplication, QWidget, QVBoxLayout, QLineEdit,
                             QPushButton, QLabel, QMessageBox)
from PyQt6.QtCore import QThread, pyqtSignal

SIGROK_PATH = r"C:\Program Files\sigrok\sigrok-cli\sigrok-cli.exe"

class CaptureThread(QThread):
    data_ready = pyqtSignal(np.ndarray, float) # Sends data and the frequency used
    error_msg = pyqtSignal(str)

    def __init__(self, freq_str, count):
        super().__init__()
        self.freq_str = freq_str
        self.count = count

    def run(self):
        # Convert frequency string (e.g. '1m') to float for math later
        multiplier = {'k': 1e3, 'm': 1e6, 'g': 1e9}
        try:
            val = float(''.join(filter(str.isdigit, self.freq_str)))
            unit = ''.join(filter(str.isalpha, self.freq_str)).lower()
            freq_hz = val * multiplier.get(unit, 1)
        except:
            freq_hz = 1e6 # Default fallback

        cmd = [SIGROK_PATH, "--driver", "raspberrypi-pico:conn=COM15",
               "--config", f"samplerate={self.freq_str}", "--samples", str(self.count), "-O", "binary"]

        try:
            result = subprocess.run(cmd, capture_output=True, timeout=10)
            if result.returncode != 0:
                self.error_msg.emit(result.stderr.decode())
                return

            raw_data = np.frombuffer(result.stdout, dtype=np.uint8)
            self.data_ready.emit(raw_data, freq_hz)
        except Exception as e:
            self.error_msg.emit(str(e))

class PicoLogicApp(QWidget):
    def __init__(self):
        super().__init__()
        self.initUI()

    def initUI(self):
        layout = QVBoxLayout(self)
        self.freq_in = QLineEdit("1m")
        self.count_in = QLineEdit("50000")
        self.btn = QPushButton("🚀 Capture (Time Scaled)")
        self.btn.clicked.connect(self.start_capture)

        self.pw = pg.PlotWidget()
        self.pw.setBackground('k')
        self.pw.setLabel('bottom', 'Time', units='s') # Adds 's' for seconds

        # Channel Labels
        ay = self.pw.getAxis('left')
        ay.setTicks([[(i * 2, f"D{i}") for i in range(8)]])
        self.pw.setYRange(-0.5, 15)

        layout.addWidget(QLabel("Sample Rate (100k, 1m, 10m):"))
        layout.addWidget(self.freq_in)
        layout.addWidget(QLabel("Sample Count:"))
        layout.addWidget(self.count_in)
        layout.addWidget(self.btn)
        layout.addWidget(self.pw)
        self.resize(1000, 600)

    def start_capture(self):
        self.btn.setEnabled(False)
        self.pw.clear()
        self.worker = CaptureThread(self.freq_in.text(), self.count_in.text())
        self.worker.data_ready.connect(self.plot_data)
        self.worker.error_msg.connect(self.show_error)
        self.worker.start()

    def plot_data(self, data, freq_hz):
        if data.size == 0: return

        # ⚡ Downsampling for smoothness
        limit = 50000
        factor = max(1, len(data) // limit)
        d_view = data[::factor]

        # ⏰ Time Calculation
        # Duration of one 'downsampled' step
        time_per_step = factor / freq_hz
        x_axis = np.arange(len(d_view) + 1) * time_per_step

        for i in range(8):
            y = ((d_view >> i) & 1).astype(np.float32) + (i * 2)

            # StepMode digital look with Time Scaling
            self.pw.plot(x_axis, y, pen=pg.mkPen(pg.intColor(i), width=2), stepMode="center")

        self.pw.autoRange()
        self.btn.setEnabled(True)

    def show_error(self, msg):
        QMessageBox.warning(self, "Error", msg)
        self.btn.setEnabled(True)

if __name__ == '__main__':
    app = QApplication(sys.argv)
    ex = PicoLogicApp(); ex.show()
    sys.exit(app.exec())
