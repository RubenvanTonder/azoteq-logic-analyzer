import sys
import serial
import serial.tools.list_ports
import numpy as np
import pyqtgraph as pg
from PyQt5.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
                             QLabel, QComboBox, QSpinBox, QDoubleSpinBox, QPushButton,
                             QGroupBox, QCheckBox, QTextEdit, QTabWidget, QGridLayout,
                             QMessageBox, QSplitter, QRadioButton, QButtonGroup)
from PyQt5.QtCore import QThread, pyqtSignal, Qt, QTimer

# ==========================================
# CONFIGURATION
# ==========================================
MIN_SAMPLE_RATE = 5000
MAX_SAMPLE_RATE = 500000
ADC_REF_VOLTAGE = 3.3
ADC_RESOLUTION = 256

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
        self.is_paused = False
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
                    data = self.serial_port.read(self.serial_port.in_waiting)
                    if data and not self.is_paused:
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

    def flush_buffers(self):
        if self.serial_port and self.serial_port.is_open:
            self.serial_port.reset_input_buffer()

    def stop(self):
        self.is_running = False
        self.wait()

# ==========================================
# ANALOG SCOPE
# ==========================================
class AnalogDisplay(QWidget):
    def __init__(self):
        super().__init__()
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        # Info Bar
        self.cursor_panel = QWidget()
        self.cursor_panel.setStyleSheet("background: #252526; color: #ddd; border-bottom: 1px solid #444;")
        cp_layout = QHBoxLayout(self.cursor_panel)
        cp_layout.setContentsMargins(10, 5, 10, 5)

        self.lbl_dt = QLabel("ΔT: -- ms")
        self.lbl_dv = QLabel("ΔV: -- V")
        self.lbl_dt.setStyleSheet("font-weight: bold; color: #4caf50;")
        self.lbl_dv.setStyleSheet("font-weight: bold; color: #ff9800;")

        self.chk_cursors = QCheckBox("Cursors")
        self.chk_cursors.stateChanged.connect(self.toggle_cursors)
        self.chk_cursors.setStyleSheet("color: white;")

        cp_layout.addWidget(self.chk_cursors)
        cp_layout.addWidget(self.lbl_dt)
        cp_layout.addWidget(self.lbl_dv)
        cp_layout.addStretch()
        layout.addWidget(self.cursor_panel)

        # Graph
        pg.setConfigOption('background', '#121212')
        pg.setConfigOption('foreground', '#d0d0d0')
        pg.setConfigOption('antialias', True)

        self.plot_widget = pg.PlotWidget(title="ADC Scope")
        self.plot_widget.showGrid(x=True, y=True, alpha=0.2)
        self.plot_widget.setYRange(-0.1, 3.5)
        self.plot_widget.setLabel('left', 'Voltage', units='V')
        layout.addWidget(self.plot_widget)

        self.buffer_size = 5000
        self.sample_rate = 100000
        self.active_channels = [True, False]

        self.data_a1 = np.zeros(self.buffer_size)
        self.data_a2 = np.zeros(self.buffer_size)

        self.curve_a1 = self.plot_widget.plot(pen=pg.mkPen('#00e5ff', width=2), name="A1")
        self.curve_a2 = self.plot_widget.plot(pen=pg.mkPen('#ff4081', width=2), name="A2")

        # Cursors
        self.v_cursor1 = pg.InfiniteLine(pos=1000, angle=90, movable=True, pen='g')
        self.v_cursor2 = pg.InfiniteLine(pos=2000, angle=90, movable=True, pen='g')
        self.h_cursor1 = pg.InfiniteLine(pos=1.0, angle=0, movable=True, pen='y')
        self.h_cursor2 = pg.InfiniteLine(pos=2.0, angle=0, movable=True, pen='y')

        for line in [self.v_cursor1, self.v_cursor2, self.h_cursor1, self.h_cursor2]:
            line.sigPositionChanged.connect(self.update_cursor_readout)
            line.setVisible(False)
            self.plot_widget.addItem(line)

        # Timer
        self.needs_redraw = False
        self.render_timer = QTimer()
        self.render_timer.timeout.connect(self.update_plot_visuals)
        self.render_timer.start(33)

    def toggle_cursors(self, state):
        visible = (state == Qt.Checked)
        for line in [self.v_cursor1, self.v_cursor2, self.h_cursor1, self.h_cursor2]:
            line.setVisible(visible)
        if visible: self.update_cursor_readout()

    def update_cursor_readout(self):
        t1, t2 = self.v_cursor1.value(), self.v_cursor2.value()
        delta_samples = abs(t2 - t1)
        if self.sample_rate > 0:
            delta_ms = (delta_samples / self.sample_rate) * 1000
            self.lbl_dt.setText(f"ΔT: {delta_ms:.2f} ms")

        v1, v2 = self.h_cursor1.value(), self.h_cursor2.value()
        self.lbl_dv.setText(f"ΔV: {abs(v2-v1):.3f} V")

    def set_active_channels(self, a1_en, a2_en, rate):
        self.active_channels = [a1_en, a2_en]
        self.sample_rate = rate
        self.curve_a1.setVisible(a1_en)
        self.curve_a2.setVisible(a2_en)
        self.clear()

    def update_data(self, new_bytes):
        if len(new_bytes) == 0: return
        raw = np.frombuffer(new_bytes, dtype=np.uint8)
        voltage = (raw / ADC_RESOLUTION) * ADC_REF_VOLTAGE

        a1_active, a2_active = self.active_channels

        if a1_active and a2_active:
            self._append_buffer(voltage[0::2], 1)
            self._append_buffer(voltage[1::2], 2)
        elif a1_active:
            self._append_buffer(voltage, 1)
        elif a2_active:
            self._append_buffer(voltage, 2)
        self.needs_redraw = True

    def _append_buffer(self, new_data, channel):
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
        if self.active_channels[0]: self.curve_a1.setData(x, self.data_a1)
        if self.active_channels[1]: self.curve_a2.setData(x, self.data_a2)
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
        self.setWindowTitle("Pico Scope (Adjustable Length)")
        self.resize(1200, 800)

        self.worker = SerialWorker()
        self.worker.data_received.connect(self.process_serial_data)
        self.worker.connection_status.connect(self.update_connection_status)
        self.worker.error_occurred.connect(self.handle_error)

        central = QWidget()
        self.setCentralWidget(central)
        main_split = QSplitter(Qt.Vertical)

        # Top Bar
        top_widget = QWidget()
        top_layout = QHBoxLayout(top_widget)
        self.create_conn_group(top_layout)
        self.create_adc_group(top_layout)
        self.create_pwm_group(top_layout)
        self.create_run_group(top_layout)
        top_layout.addStretch()
        main_split.addWidget(top_widget)

        # Scope
        self.scope_view = AnalogDisplay()
        main_split.addWidget(self.scope_view)

        # Logs
        self.create_monitor_tabs()
        main_split.addWidget(self.monitor_tabs)

        main_split.setSizes([180, 570, 150])
        layout = QVBoxLayout(central)
        layout.addWidget(main_split)

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
        group.setLayout(layout)
        parent_layout.addWidget(group)

    def create_adc_group(self, parent_layout):
        group = QGroupBox("2. ADC Input")
        layout = QGridLayout()

        # Rate
        layout.addWidget(QLabel("Rate (Hz):"), 0, 0)
        self.rate_spin = QSpinBox()
        self.rate_spin.setRange(MIN_SAMPLE_RATE, MAX_SAMPLE_RATE)
        self.rate_spin.setValue(100000)
        layout.addWidget(self.rate_spin, 0, 1)

        # Channels
        self.chk_a1 = QCheckBox("Enable A1")
        self.chk_a1.setChecked(True)
        self.chk_a1.setStyleSheet("color: #00e5ff;")
        self.chk_a2 = QCheckBox("Enable A2")
        self.chk_a2.setStyleSheet("color: #ff4081;")

        layout.addWidget(self.chk_a1, 1, 0)
        layout.addWidget(self.chk_a2, 1, 1)

        group.setLayout(layout)
        parent_layout.addWidget(group)

    def create_pwm_group(self, parent_layout):
        group = QGroupBox("3. PWM Output")
        layout = QGridLayout()

        layout.addWidget(QLabel("Target:"), 0, 0)
        self.pwm_ch = QComboBox()
        self.pwm_ch.addItems(["PWM1", "PWM2"])
        layout.addWidget(self.pwm_ch, 0, 1)

        layout.addWidget(QLabel("Freq (kHz):"), 1, 0)
        self.pwm_freq = QSpinBox()
        self.pwm_freq.setRange(1, 20000)
        self.pwm_freq.setValue(1000)
        layout.addWidget(self.pwm_freq, 1, 1)

        layout.addWidget(QLabel("Duty (%):"), 2, 0)
        self.pwm_duty = QDoubleSpinBox()
        self.pwm_duty.setRange(0.0, 100.0)
        self.pwm_duty.setValue(50.0)
        layout.addWidget(self.pwm_duty, 2, 1)

        btn_set = QPushButton("Set PWM")
        btn_set.clicked.connect(self.send_pwm_cmd)
        layout.addWidget(btn_set, 3, 0, 1, 2)
        group.setLayout(layout)
        parent_layout.addWidget(group)

    def create_run_group(self, parent_layout):
        group = QGroupBox("4. Control")
        layout = QVBoxLayout()

        # --- NEW: Mode Selection ---
        mode_row = QHBoxLayout()
        self.rb_cont = QRadioButton("Cont.")
        self.rb_fixed = QRadioButton("Fixed")
        self.rb_cont.setChecked(True)

        self.rb_cont.toggled.connect(self.update_run_button_text)

        grp = QButtonGroup(self)
        grp.addButton(self.rb_cont)
        grp.addButton(self.rb_fixed)

        mode_row.addWidget(self.rb_cont)
        mode_row.addWidget(self.rb_fixed)
        layout.addLayout(mode_row)

        # --- NEW: Sample Length ---
        len_row = QHBoxLayout()
        len_row.addWidget(QLabel("Len:"))
        self.len_spin = QSpinBox()
        self.len_spin.setRange(100, 1000000)
        self.len_spin.setValue(5000) # Default
        len_row.addWidget(self.len_spin)
        layout.addLayout(len_row)

        self.btn_run = QPushButton("START STREAM")
        self.btn_run.setMinimumHeight(35)
        self.btn_run.setStyleSheet("background: #28a745; color: white; font-weight: bold;")
        self.btn_run.clicked.connect(self.restart_scope_sequence)

        self.btn_stop = QPushButton("STOP")
        self.btn_stop.setStyleSheet("background: #dc3545; color: white;")
        self.btn_stop.clicked.connect(self.worker.stop)

        layout.addWidget(self.btn_run)
        layout.addWidget(self.btn_stop)
        group.setLayout(layout)
        parent_layout.addWidget(group)

    def create_monitor_tabs(self):
        self.monitor_tabs = QTabWidget()
        self.monitor_tabs.setMaximumHeight(150)
        self.log_view = QTextEdit()
        self.log_view.setReadOnly(True)
        self.log_view.setStyleSheet("font-family: Monospace; font-size: 9pt;")
        self.monitor_tabs.addTab(self.log_view, "Log")

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

    def update_run_button_text(self):
        if self.rb_cont.isChecked():
            self.btn_run.setText("START STREAM")
        else:
            self.btn_run.setText("CAPTURE FIXED")

    def send_pwm_cmd(self):
        ch = 1 if self.pwm_ch.currentIndex() == 0 else 2
        cmd = f"W{ch},{self.pwm_freq.value()},{self.pwm_duty.value():.1f}"
        self.log_msg(f"Set PWM: {cmd}")
        self.send_cmd(cmd)

    def restart_scope_sequence(self):
        if not self.worker.isRunning():
            QMessageBox.warning(self, "Error", "Not Connected")
            return

        self.btn_run.setEnabled(False)
        self.btn_run.setText("Syncing...")

        # 1. Pause & Reset
        self.worker.is_paused = True
        self.send_cmd("*")

        # 2. Wait for HW reset
        QTimer.singleShot(100, self._finish_scope_start)

    def _finish_scope_start(self):
        self.worker.flush_buffers()

        a1, a2 = self.chk_a1.isChecked(), self.chk_a2.isChecked()
        rate = self.rate_spin.value()
        length = self.len_spin.value()

        # Update Visuals
        self.scope_view.set_active_channels(a1, a2, rate)

        # Config Commands
        self.send_cmd(f"R{rate}")
        self.send_cmd(f"L{length}") # Dynamic Length
        self.send_cmd(f"A{'1' if a1 else '0'}0")
        self.send_cmd(f"A{'1' if a2 else '0'}1")

        # Trigger Mode
        if self.rb_cont.isChecked():
            self.send_cmd("C") # Continuous
        else:
            self.send_cmd("F") # Fixed (stops after L samples)

        self.worker.is_paused = False
        self.btn_run.setEnabled(True)
        self.update_run_button_text()

    def send_cmd(self, command_str):
        if not self.worker.isRunning(): return
        if command_str not in ["C", "*"]:
            self.log_msg(f"TX -> {command_str}")
        self.worker.send_data(command_str)

    def process_serial_data(self, data):
        self.scope_view.update_data(data)

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
