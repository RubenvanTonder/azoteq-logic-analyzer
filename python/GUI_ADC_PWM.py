import sys
import serial
import serial.tools.list_ports
import numpy as np
import pyqtgraph as pg
from PyQt5.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
                             QLabel, QComboBox, QSpinBox, QDoubleSpinBox, QPushButton,
                             QGroupBox, QCheckBox, QTextEdit, QTabWidget, QGridLayout,
                             QMessageBox, QSplitter, QScrollArea)
from PyQt5.QtCore import QThread, pyqtSignal, Qt, QTimer

# ==========================================
# CONFIGURATION
# ==========================================
MIN_SAMPLE_RATE = 5000
MAX_SAMPLE_RATE = 500000 # ADC is slower than Digital (adjust based on your firmware)
ADC_REF_VOLTAGE = 3.3
ADC_RESOLUTION = 256     # Assuming 8-bit transfer (0-255). Change to 4096 if 12-bit.

# ==========================================
# SERIAL WORKER
# ==========================================
class SerialWorker(QThread):
    data_received = pyqtSignal(bytes)
    error_occurred = pyqtSignal(str)
    connection_status = pyqtSignal(bool)

    def __init__(self):
        super().__init__()
        self.serial_port = None
        self.is_running = False
        self.port_name = ""
        self.baud_rate = 115200

    def connect_serial(self, port, baud):
        self.port_name = port
        self.baud_rate = baud
        self.start()

    def run(self):
        try:
            self.serial_port = serial.Serial(self.port_name, self.baud_rate, timeout=0.1)
            self.is_running = True
            self.connection_status.emit(True)
            while self.is_running:
                if self.serial_port.in_waiting:
                    # Read raw ADC stream
                    data = self.serial_port.read(self.serial_port.in_waiting)
                    if data:
                        self.data_received.emit(data)
                    self.msleep(2)
                else:
                    self.msleep(10)
        except Exception as e:
            self.error_occurred.emit(str(e))
            self.connection_status.emit(False)
        finally:
            if self.serial_port and self.serial_port.is_open:
                self.serial_port.close()

    def send_data(self, data):
        if self.serial_port and self.serial_port.is_open:
            try:
                self.serial_port.write(data.encode('utf-8') + b'\n')
            except Exception as e:
                self.error_occurred.emit(str(e))

    def stop(self):
        self.is_running = False
        self.wait()

# ==========================================
# ANALOG OSCILLOSCOPE DISPLAY
# ==========================================
class AnalogDisplay(QWidget):
    def __init__(self):
        super().__init__()
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        # Styling
        pg.setConfigOption('background', '#121212')
        pg.setConfigOption('foreground', '#d0d0d0')
        pg.setConfigOption('antialias', True) # Smooth lines for Analog

        self.plot_widget = pg.PlotWidget(title="Real-Time ADC Scope")
        self.plot_widget.showGrid(x=True, y=True, alpha=0.2)
        self.plot_widget.setYRange(-0.1, 3.5) # Fixed 0-3.3V range with padding
        self.plot_widget.setLabel('left', 'Voltage', units='V')
        self.plot_widget.setLabel('bottom', 'Samples')
        layout.addWidget(self.plot_widget)

        self.buffer_size = 5000
        self.active_channels = [True, False] # A1, A2 state tracking

        # Data Buffers
        self.data_a1 = np.zeros(self.buffer_size)
        self.data_a2 = np.zeros(self.buffer_size)

        # Curves
        self.curve_a1 = self.plot_widget.plot(pen=pg.mkPen('#00e5ff', width=2), name="A1")
        self.curve_a2 = self.plot_widget.plot(pen=pg.mkPen('#ff4081', width=2), name="A2")

        # Labels
        self.legend = pg.LegendItem(offset=(60, 20))
        self.legend.setParentItem(self.plot_widget.graphicsItem())
        self.legend.addItem(self.curve_a1, "ADC 1")
        self.legend.addItem(self.curve_a2, "ADC 2")

        # 30FPS Render Loop
        self.needs_redraw = False
        self.render_timer = QTimer()
        self.render_timer.timeout.connect(self.update_plot_visuals)
        self.render_timer.start(33)

    def set_active_channels(self, a1_en, a2_en):
        """Updates scaling and visibility based on active inputs"""
        self.active_channels = [a1_en, a2_en]
        self.curve_a1.setVisible(a1_en)
        self.curve_a2.setVisible(a2_en)
        self.clear()

    def update_data(self, new_bytes):
        if len(new_bytes) == 0: return

        # Convert raw bytes to Voltage
        # Assumption: Data is 8-bit unsigned (0..255) -> 0..3.3V
        raw = np.frombuffer(new_bytes, dtype=np.uint8)
        voltage = (raw / ADC_RESOLUTION) * ADC_REF_VOLTAGE

        a1_active, a2_active = self.active_channels

        # --- De-interleaving Logic ---
        if a1_active and a2_active:
            # Format: A1, A2, A1, A2...
            # Split into even/odd indices
            v1 = voltage[0::2]
            v2 = voltage[1::2]

            # Safely roll buffer
            self._append_buffer(v1, 1)
            self._append_buffer(v2, 2)

        elif a1_active:
            # All data is A1
            self._append_buffer(voltage, 1)

        elif a2_active:
            # All data is A2
            self._append_buffer(voltage, 2)

        self.needs_redraw = True

    def _append_buffer(self, new_data, channel):
        """Helper to roll circular buffers"""
        count = len(new_data)
        if count == 0: return

        if channel == 1:
            if count < self.buffer_size:
                self.data_a1 = np.roll(self.data_a1, -count)
                self.data_a1[-count:] = new_data
            else:
                self.data_a1 = new_data[-self.buffer_size:]
        else:
            if count < self.buffer_size:
                self.data_a2 = np.roll(self.data_a2, -count)
                self.data_a2[-count:] = new_data
            else:
                self.data_a2 = new_data[-self.buffer_size:]

    def update_plot_visuals(self):
        if not self.needs_redraw: return

        x = np.arange(self.buffer_size)
        if self.active_channels[0]:
            self.curve_a1.setData(x, self.data_a1)
        if self.active_channels[1]:
            self.curve_a2.setData(x, self.data_a2)

        self.needs_redraw = False

    def clear(self):
        self.data_a1.fill(0)
        self.data_a2.fill(0)
        self.needs_redraw = True

# ==========================================
# MAIN GUI
# ==========================================
class PicoAnalogGUI(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Pico Oscilloscope & PWM Controller")
        self.resize(1200, 800)

        self.worker = SerialWorker()
        self.worker.data_received.connect(self.process_serial_data)
        self.worker.connection_status.connect(self.update_connection_status)
        self.worker.error_occurred.connect(self.handle_error)

        # Main Layout
        central = QWidget()
        self.setCentralWidget(central)
        main_split = QSplitter(Qt.Vertical)

        # --- Top Panel (Settings) ---
        top_widget = QWidget()
        top_layout = QHBoxLayout(top_widget)

        # Group 1: Connection
        self.create_conn_group(top_layout)

        # Group 2: ADC Config
        self.create_adc_group(top_layout)

        # Group 3: PWM Generator
        self.create_pwm_group(top_layout)

        # Group 4: Run Control
        self.create_run_group(top_layout)

        top_layout.addStretch()
        main_split.addWidget(top_widget)

        # --- Middle: Oscilloscope ---
        self.scope_view = AnalogDisplay()
        main_split.addWidget(self.scope_view)

        # --- Bottom: Logs ---
        self.create_monitor_tabs()
        main_split.addWidget(self.monitor_tabs)

        # Sizes: Top(20%), Scope(60%), Logs(20%)
        main_split.setSizes([150, 600, 150])

        layout = QVBoxLayout(central)
        layout.addWidget(main_split)

    # ================= UI BUILDERS =================

    def create_conn_group(self, parent_layout):
        group = QGroupBox("1. Connection")
        layout = QVBoxLayout()

        self.port_combo = QComboBox()
        self.refresh_ports()

        row = QHBoxLayout()
        btn_ref = QPushButton("R")
        btn_ref.setFixedWidth(30)
        btn_ref.clicked.connect(self.refresh_ports)
        row.addWidget(self.port_combo)
        row.addWidget(btn_ref)

        self.connect_btn = QPushButton("Connect")
        self.connect_btn.setCheckable(True)
        self.connect_btn.clicked.connect(self.toggle_connection)

        layout.addLayout(row)
        layout.addWidget(self.connect_btn)
        layout.addStretch()
        group.setLayout(layout)
        parent_layout.addWidget(group)

    def create_adc_group(self, parent_layout):
        group = QGroupBox("2. ADC Input")
        layout = QGridLayout()

        # Rate
        layout.addWidget(QLabel("Sample Rate:"), 0, 0)
        self.rate_spin = QSpinBox()
        self.rate_spin.setRange(MIN_SAMPLE_RATE, MAX_SAMPLE_RATE)
        self.rate_spin.setValue(100000)
        self.rate_spin.setSuffix(" Hz")
        layout.addWidget(self.rate_spin, 0, 1)

        # Channels
        self.chk_a1 = QCheckBox("Enable A1 (GP41)")
        self.chk_a1.setChecked(True)
        self.chk_a1.setStyleSheet("color: #00e5ff; font-weight: bold;")

        self.chk_a2 = QCheckBox("Enable A2 (GP42)")
        self.chk_a2.setStyleSheet("color: #ff4081; font-weight: bold;")

        layout.addWidget(self.chk_a1, 1, 0, 1, 2)
        layout.addWidget(self.chk_a2, 2, 0, 1, 2)

        group.setLayout(layout)
        parent_layout.addWidget(group)

    def create_pwm_group(self, parent_layout):
        group = QGroupBox("3. PWM Output")
        layout = QGridLayout()

        # Channel
        layout.addWidget(QLabel("Target:"), 0, 0)
        self.pwm_ch = QComboBox()
        self.pwm_ch.addItems(["PWM1 (GP12)", "PWM2 (GP13)"])
        layout.addWidget(self.pwm_ch, 0, 1)

        # Frequency
        layout.addWidget(QLabel("Freq:"), 1, 0)
        self.pwm_freq = QSpinBox()
        self.pwm_freq.setRange(1, 20000)
        self.pwm_freq.setValue(1000)
        self.pwm_freq.setSuffix(" kHz")
        layout.addWidget(self.pwm_freq, 1, 1)

        # Duty
        layout.addWidget(QLabel("Duty:"), 2, 0)
        self.pwm_duty = QDoubleSpinBox()
        self.pwm_duty.setRange(0.0, 100.0)
        self.pwm_duty.setValue(50.0)
        self.pwm_duty.setSuffix("%")
        layout.addWidget(self.pwm_duty, 2, 1)

        btn_set = QPushButton("Update PWM")
        btn_set.clicked.connect(self.send_pwm_cmd)
        layout.addWidget(btn_set, 3, 0, 1, 2)

        group.setLayout(layout)
        parent_layout.addWidget(group)

    def create_run_group(self, parent_layout):
        group = QGroupBox("4. Control")
        layout = QVBoxLayout()

        btn_run = QPushButton("START SCOPE")
        btn_run.setMinimumHeight(40)
        btn_run.setStyleSheet("background: #28a745; color: white; font-weight: bold;")
        btn_run.clicked.connect(self.run_sequence)

        btn_stop = QPushButton("STOP")
        btn_stop.setStyleSheet("background: #dc3545; color: white;")
        btn_stop.clicked.connect(self.worker.stop)

        btn_id = QPushButton("Identify Device")
        btn_id.clicked.connect(lambda: self.send_cmd("i"))

        layout.addWidget(btn_run)
        layout.addWidget(btn_stop)
        layout.addWidget(btn_id)
        group.setLayout(layout)
        parent_layout.addWidget(group)

    def create_monitor_tabs(self):
        self.monitor_tabs = QTabWidget()
        self.monitor_tabs.setMaximumHeight(200) # Keep it small

        self.log_view = QTextEdit()
        self.log_view.setReadOnly(True)
        self.log_view.setStyleSheet("font-family: Monospace; font-size: 9pt;")
        self.monitor_tabs.addTab(self.log_view, "System Log")

    # ================= LOGIC =================

    def refresh_ports(self):
        self.port_combo.clear()
        ports = serial.tools.list_ports.comports()
        for port in ports:
            self.port_combo.addItem(f"{port.device}", port.device)

    def toggle_connection(self):
        if self.connect_btn.isChecked():
            port = self.port_combo.currentData()
            if port:
                self.worker.connect_serial(port, 115200)
                self.log_msg(f"Connecting to {port}...")
            else:
                self.connect_btn.setChecked(False)
        else:
            self.worker.stop()
            self.log_msg("Disconnected.")

    def update_connection_status(self, connected):
        if connected:
            self.connect_btn.setText("Disconnect")
            self.connect_btn.setStyleSheet("background-color: #c3e6cb;")
            self.send_cmd("i")
        else:
            self.connect_btn.setChecked(False)
            self.connect_btn.setText("Connect")
            self.connect_btn.setStyleSheet("")

    def send_pwm_cmd(self):
        # Protocol: W<channel>,<freq_khz>,<duty>
        ch = 1 if self.pwm_ch.currentIndex() == 0 else 2
        freq = self.pwm_freq.value()
        duty = self.pwm_duty.value()
        cmd = f"W{ch},{freq},{duty:.1f}"
        self.log_msg(f"Setting PWM: {cmd}")
        self.send_cmd(cmd)

    def run_sequence(self):
        if not self.worker.isRunning():
            QMessageBox.warning(self, "Error", "Not Connected")
            return

        # 1. Update Visualizer Context
        a1 = self.chk_a1.isChecked()
        a2 = self.chk_a2.isChecked()
        self.scope_view.set_active_channels(a1, a2)

        # 2. Send Rate (R)
        self.send_cmd(f"R{self.rate_spin.value()}")

        # 3. Send Sample Limit (L) - Set high for continuous feel
        self.send_cmd(f"L50000")

        # 4. Send Analog Masks (A) - CRITICAL
        # Protocol: A<state><channel> e.g. A10 (Enable Ch0), A01 (Disable Ch1)
        # Assuming firmware indices: A1 -> 0, A2 -> 1
        self.send_cmd(f"A{'1' if a1 else '0'}0")
        self.send_cmd(f"A{'1' if a2 else '0'}1")

        # 5. Start Continuous (C) or Fixed (F)
        # Use Continuous for Scope feel
        self.send_cmd("C")

    def send_cmd(self, command_str):
        if not self.worker.isRunning(): return
        # Only log non-data commands
        if command_str not in ["C", "F"]:
            self.log_msg(f"TX -> {command_str}")
        self.worker.send_data(command_str)

    def process_serial_data(self, data):
        # 1. Visuals
        self.scope_view.update_data(data)

        # 2. Logs (Strict Filtering)
        try:
            text = data.decode('utf-8')
            # Only log specific protocol responses (starts with ID, etc)
            if any(x in text for x in ["SRPICO", "PWM", "Error", "SMPRATE"]):
                self.log_msg(f"RX <- {text.strip()}")
        except: pass

    def log_msg(self, text):
        self.log_view.append(text)
        sb = self.log_view.verticalScrollBar()
        sb.setValue(sb.maximum())

    def handle_error(self, msg):
        QMessageBox.critical(self, "Error", msg)
        self.connect_btn.setChecked(False)

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = PicoAnalogGUI()
    window.show()
    sys.exit(app.exec_())
